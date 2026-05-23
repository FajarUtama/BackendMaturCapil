from collections import defaultdict
from datetime import timedelta

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.constants import ADMIN_ROLES, CITIZEN_ROLE
from app.core.deps import get_client_ip, get_current_user, require_citizen
from app.core.responses import error_response, raise_api_error, success_response
from app.core.security import verify_password
from app.database import get_db
from app.models.email_verification import EmailVerification, PendingRegistration
from app.models.user import User
from app.schemas.auth import (
    EmailOtpVerifyRequest,
    LoginRequest,
    OtpVerifyRequest,
    RegisterRequest,
    ResendOtpRequest,
)
from app.services.audit import write_audit_log
from app.services.auth_tokens import issue_tokens, revoke_refresh_tokens
from app.services.email_service import send_otp_email
from app.core.security import hash_password
from app.services.otp_service import (
    check_resend_allowed,
    generate_otp,
    otp_expires_at,
    verify_otp_code,
)
from app.services.user_service import serialize_user
from app.utils.datetime_utils import utcnow
from app.utils.ids import new_id
from app.utils.validation import validate_nik, validate_password

router = APIRouter(prefix="/auth", tags=["Autentikasi"])
settings = get_settings()

_login_attempts: dict[str, list[float]] = defaultdict(list)


def _check_login_rate_limit(email: str) -> None:
    key = email.lower()
    now = utcnow().timestamp()
    window = settings.login_window_minutes * 60
    _login_attempts[key] = [t for t in _login_attempts[key] if now - t < window]
    if len(_login_attempts[key]) >= settings.login_max_attempts:
        raise_api_error("Terlalu banyak percobaan login. Coba lagi dalam 15 menit.", 429)


def _record_failed_login(email: str) -> None:
    _login_attempts[email.lower()].append(utcnow().timestamp())


@router.post("/login")
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    _check_login_rate_limit(email)

    user = db.query(User).filter(User.email == email, User.deleted_at.is_(None)).first()
    if not user or not verify_password(body.password, user.password_hash):
        _record_failed_login(email)
        raise_api_error("Email atau password salah.", 401)

    if user.status == "INACTIVE":
        raise_api_error("Akun dinonaktifkan.", 403)
    if user.status == "SUSPENDED":
        raise_api_error("Akun ditangguhkan.", 403)

    if body.portal == "citizen" and user.role != CITIZEN_ROLE:
        raise_api_error("Gunakan Portal Admin.", 403)
    if body.portal == "admin" and user.role not in ADMIN_ROLES:
        raise_api_error("Gunakan Portal Warga.", 403)

    _login_attempts[email] = []
    data = issue_tokens(db, user)
    write_audit_log(
        db,
        user_id=user.id,
        action="LOGIN",
        detail=f"Login via portal {body.portal}",
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()
    return success_response(data=data, message="Login berhasil")


@router.post("/logout")
def logout(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    revoke_refresh_tokens(db, user.id)
    write_audit_log(
        db,
        user_id=user.id,
        action="LOGOUT",
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()
    return success_response(message="Logout berhasil")


@router.get("/me")
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return success_response(data=serialize_user(user, db))


@router.post("/register")
async def register(body: RegisterRequest, db: Session = Depends(get_db)):
    if body.password != body.password_confirmation:
        raise_api_error("Konfirmasi password tidak cocok.", 400, errors={"password_confirmation": ["Tidak cocok."]})

    pw_errors = validate_password(body.password)
    if pw_errors:
        raise_api_error("Validasi password gagal.", 400, errors={"password": pw_errors})

    nik_errors = validate_nik(body.nik)
    if nik_errors:
        raise_api_error("Validasi NIK gagal.", 400, errors={"nik": nik_errors})

    email = body.email.strip().lower()
    if db.query(User).filter(User.email == email).first():
        raise_api_error("Email sudah terdaftar.", 400, errors={"email": ["Email sudah terdaftar."]})
    if db.query(User).filter(User.nik == body.nik).first():
        raise_api_error("NIK sudah terdaftar.", 400, errors={"nik": ["NIK sudah terdaftar."]})

    db.query(PendingRegistration).filter(PendingRegistration.email == email).delete()
    otp = generate_otp()
    pending = PendingRegistration(
        id=new_id("preg"),
        name=body.name.strip(),
        nik=body.nik,
        email=email,
        password_hash=hash_password(body.password),
        otp_code=otp,
        expired_at=otp_expires_at(),
        last_sent_at=utcnow(),
    )
    db.add(pending)
    db.commit()
    await send_otp_email(email, otp, "registrasi")
    return success_response(
        data={"email": email},
        message="Kode OTP telah dikirim ke email Anda. Berlaku 5 menit.",
    )


@router.post("/register/verify-otp")
async def register_verify_otp(body: OtpVerifyRequest, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    pending = db.query(PendingRegistration).filter(PendingRegistration.email == email).first()
    if not pending:
        raise_api_error("Sesi registrasi tidak ditemukan. Daftar ulang.", 400)

    verify_otp_code(pending.otp_code, body.otp, pending.expired_at)

    if db.query(User).filter(User.email == email).first():
        db.delete(pending)
        db.commit()
        raise_api_error("Email sudah terdaftar.", 400)

    user = User(
        id=new_id("usr"),
        name=pending.name,
        nik=pending.nik,
        email=pending.email,
        password_hash=pending.password_hash,
        role=CITIZEN_ROLE,
        status="ACTIVE",
        email_verified_at=utcnow(),
    )
    db.add(user)
    db.delete(pending)
    db.flush()
    data = issue_tokens(db, user)
    db.commit()
    return success_response(data=data, message="Registrasi berhasil")


@router.post("/register/resend-otp")
async def register_resend_otp(body: ResendOtpRequest, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    pending = db.query(PendingRegistration).filter(PendingRegistration.email == email).first()
    if not pending:
        raise_api_error("Sesi registrasi tidak ditemukan.", 400)

    check_resend_allowed(pending.resend_count, pending.last_sent_at)
    pending.resend_count += 1
    pending.otp_code = generate_otp()
    pending.expired_at = otp_expires_at()
    pending.last_sent_at = utcnow()
    db.commit()
    await send_otp_email(email, pending.otp_code, "registrasi")
    return success_response(message="OTP baru telah dikirim.")


@router.post("/email/send-otp")
async def email_send_otp(user: User = Depends(require_citizen), db: Session = Depends(get_db)):
    if user.email_verified:
        raise_api_error("Email sudah terverifikasi.", 400)

    db.query(EmailVerification).filter(
        EmailVerification.user_id == user.id,
        EmailVerification.verified_at.is_(None),
    ).delete()

    otp = generate_otp()
    ev = EmailVerification(
        id=new_id("ev"),
        user_id=user.id,
        otp_code=otp,
        expired_at=otp_expires_at(),
        last_sent_at=utcnow(),
    )
    db.add(ev)
    db.commit()
    await send_otp_email(user.email, otp, "verifikasi email")
    return success_response(message="OTP dikirim ke email Anda.")


@router.post("/email/resend-otp")
async def email_resend_otp(user: User = Depends(require_citizen), db: Session = Depends(get_db)):
    ev = (
        db.query(EmailVerification)
        .filter(EmailVerification.user_id == user.id, EmailVerification.verified_at.is_(None))
        .order_by(EmailVerification.created_at.desc())
        .first()
    )
    if not ev:
        raise_api_error("Tidak ada OTP aktif. Minta OTP baru.", 400)

    check_resend_allowed(ev.resend_count, ev.last_sent_at)
    ev.resend_count += 1
    ev.otp_code = generate_otp()
    ev.expired_at = otp_expires_at()
    ev.last_sent_at = utcnow()
    db.commit()
    await send_otp_email(user.email, ev.otp_code, "verifikasi email")
    return success_response(message="OTP baru telah dikirim.")


@router.post("/email/verify")
def email_verify(
    body: EmailOtpVerifyRequest,
    user: User = Depends(require_citizen),
    db: Session = Depends(get_db),
):
    ev = (
        db.query(EmailVerification)
        .filter(EmailVerification.user_id == user.id, EmailVerification.verified_at.is_(None))
        .order_by(EmailVerification.created_at.desc())
        .first()
    )
    if not ev:
        raise_api_error("Tidak ada OTP aktif.", 400)

    verify_otp_code(ev.otp_code, body.otp, ev.expired_at)
    now = utcnow()
    ev.verified_at = now
    user.email_verified_at = now
    db.commit()
    return success_response(
        message="Email terverifikasi",
        data={"user": serialize_user(user, db)},
    )

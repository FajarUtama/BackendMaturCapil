from fastapi import APIRouter, Depends, Request
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.constants import ADMIN_ROLES, CITIZEN_ROLE
from app.core.deps import get_client_ip, require_permission, require_super_admin
from app.core.responses import raise_api_error, success_response
from app.core.security import hash_password
from app.database import get_db
from app.models.user import User
from app.schemas.user import (
    AdminCreateRequest,
    CitizenCreateRequest,
    PermissionsUpdateRequest,
    ResetPasswordRequest,
    UserUpdateRequest,
)
from app.services.audit import write_audit_log
from app.services.permissions import set_admin_permissions
from app.services.user_service import serialize_user
from app.utils.datetime_utils import utcnow
from app.utils.ids import new_id
from app.utils.validation import validate_nik, validate_password

router = APIRouter(prefix="/users", tags=["Manajemen User"])


@router.get("")
def list_users(
    role: str | None = None,
    search: str | None = None,
    status: str | None = None,
    page: int = 1,
    per_page: int = 20,
    user: User = Depends(require_permission("user.view")),
    db: Session = Depends(get_db),
):
    q = db.query(User).filter(User.deleted_at.is_(None))
    if role:
        if role == "Admin":
            q = q.filter(User.role.in_(("Admin", "Super Admin")))
        else:
            q = q.filter(User.role == role)
    if status:
        q = q.filter(User.status == status)
    if search:
        term = f"%{search}%"
        q = q.filter(
            or_(User.name.ilike(term), User.email.ilike(term), User.nik.ilike(term))
        )

    total = q.count()
    page = max(1, page)
    per_page = min(max(1, per_page), 100)
    items = q.order_by(User.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    mask = user.role != "Super Admin"
    return success_response(
        data={
            "items": [serialize_user(u, db, mask_sensitive=mask) for u in items],
            "meta": {"page": page, "per_page": per_page, "total": total},
        }
    )


@router.get("/{user_id}")
def get_user(
    user_id: str,
    current: User = Depends(require_permission("user.view")),
    db: Session = Depends(get_db),
):
    target = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()
    if not target:
        raise_api_error("User tidak ditemukan.", 404)
    mask = current.role != "Super Admin"
    return success_response(data=serialize_user(target, db, mask_sensitive=mask))


@router.post("/citizens")
def create_citizen(
    body: CitizenCreateRequest,
    request: Request,
    admin: User = Depends(require_permission("user.create")),
    db: Session = Depends(get_db),
):
    email = body.email.strip().lower()
    pw_errors = validate_password(body.password)
    if pw_errors:
        raise_api_error("Validasi password gagal.", 400, errors={"password": pw_errors})
    nik_errors = validate_nik(body.nik)
    if nik_errors:
        raise_api_error("Validasi NIK gagal.", 400, errors={"nik": nik_errors})
    if db.query(User).filter(User.email == email).first():
        raise_api_error("Email sudah terdaftar.", 400)
    if db.query(User).filter(User.nik == body.nik).first():
        raise_api_error("NIK sudah terdaftar.", 400)

    citizen = User(
        id=new_id("usr"),
        name=body.name.strip(),
        email=email,
        nik=body.nik,
        password_hash=hash_password(body.password),
        role=CITIZEN_ROLE,
        status="ACTIVE",
    )
    db.add(citizen)
    write_audit_log(
        db,
        user_id=admin.id,
        action="CREATE_USER",
        table_name="users",
        record_id=citizen.id,
        detail=f"Membuat warga {citizen.email}",
        ip_address=get_client_ip(request),
    )
    db.commit()
    return success_response(
        data={
            "id": citizen.id,
            "role": citizen.role,
            "email_verified": False,
            "status": citizen.status,
        },
        status_code=201,
    )


@router.post("/admins")
def create_admin(
    body: AdminCreateRequest,
    request: Request,
    admin: User = Depends(require_permission("user.create")),
    db: Session = Depends(get_db),
):
    email = body.email.strip().lower()
    pw_errors = validate_password(body.password)
    if pw_errors:
        raise_api_error("Validasi password gagal.", 400, errors={"password": pw_errors})
    if db.query(User).filter(User.email == email).first():
        raise_api_error("Email sudah terdaftar.", 400)

    nik = body.nik
    if nik:
        nik_errors = validate_nik(nik)
        if nik_errors:
            raise_api_error("Validasi NIK gagal.", 400, errors={"nik": nik_errors})

    new_admin = User(
        id=new_id("usr"),
        name=body.name.strip(),
        email=email,
        nik=nik,
        password_hash=hash_password(body.password),
        role="Admin",
        status="ACTIVE",
        email_verified_at=utcnow(),
    )
    db.add(new_admin)
    db.flush()
    perms = set_admin_permissions(db, new_admin, body.permissions)
    write_audit_log(
        db,
        user_id=admin.id,
        action="CREATE_USER",
        table_name="users",
        record_id=new_admin.id,
        detail=f"Membuat admin {new_admin.email}",
        ip_address=get_client_ip(request),
    )
    db.commit()
    data = serialize_user(new_admin, db)
    data["permissions"] = perms
    return success_response(data=data, status_code=201)


@router.patch("/{user_id}")
def update_user(
    user_id: str,
    body: UserUpdateRequest,
    request: Request,
    admin: User = Depends(require_permission("user.update")),
    db: Session = Depends(get_db),
):
    target = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()
    if not target:
        raise_api_error("User tidak ditemukan.", 404)
    if target.role == "Super Admin" and admin.role != "Super Admin":
        raise_api_error("Tidak dapat mengubah Super Admin.", 403)

    if body.name is not None:
        target.name = body.name.strip()
    if body.email is not None:
        email = body.email.strip().lower()
        existing = db.query(User).filter(User.email == email, User.id != user_id).first()
        if existing:
            raise_api_error("Email sudah digunakan.", 400)
        target.email = email
    if body.nik is not None:
        nik_errors = validate_nik(body.nik)
        if nik_errors:
            raise_api_error("Validasi NIK gagal.", 400, errors={"nik": nik_errors})
        target.nik = body.nik
    if body.status is not None:
        target.status = body.status

    write_audit_log(
        db,
        user_id=admin.id,
        action="UPDATE_USER",
        table_name="users",
        record_id=target.id,
        detail=f"Memperbarui user {target.email}",
        ip_address=get_client_ip(request),
    )
    db.commit()
    mask = admin.role != "Super Admin"
    return success_response(data=serialize_user(target, db, mask_sensitive=mask))


@router.delete("/{user_id}")
def delete_user(
    user_id: str,
    request: Request,
    admin: User = Depends(require_permission("user.delete")),
    db: Session = Depends(get_db),
):
    target = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()
    if not target:
        raise_api_error("User tidak ditemukan.", 404)
    if target.role == "Super Admin":
        raise_api_error("Super Admin tidak dapat dinonaktifkan.", 403)

    target.status = "INACTIVE"
    target.deleted_at = utcnow()
    target.deleted_by = admin.id
    write_audit_log(
        db,
        user_id=admin.id,
        action="DEACTIVATE_USER",
        table_name="users",
        record_id=target.id,
        detail=f"Menonaktifkan {target.email}",
        ip_address=get_client_ip(request),
    )
    db.commit()
    return success_response(message="Akun dinonaktifkan")


@router.post("/{user_id}/reset-password")
def reset_password(
    user_id: str,
    body: ResetPasswordRequest,
    request: Request,
    admin: User = Depends(require_permission("user.update")),
    db: Session = Depends(get_db),
):
    target = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()
    if not target:
        raise_api_error("User tidak ditemukan.", 404)

    pw_errors = validate_password(body.password)
    if pw_errors:
        raise_api_error("Validasi password gagal.", 400, errors={"password": pw_errors})

    target.password_hash = hash_password(body.password)
    write_audit_log(
        db,
        user_id=admin.id,
        action="RESET_PASSWORD",
        table_name="users",
        record_id=target.id,
        detail=f"Reset password {target.email}",
        ip_address=get_client_ip(request),
    )
    db.commit()
    return success_response(message="Password direset. Email notifikasi terkirim.")


@router.put("/{user_id}/permissions")
def update_permissions(
    user_id: str,
    body: PermissionsUpdateRequest,
    request: Request,
    admin: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    target = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()
    if not target or target.role not in ("Admin",):
        raise_api_error("User admin tidak ditemukan.", 404)

    perms = set_admin_permissions(db, target, body.permissions)
    write_audit_log(
        db,
        user_id=admin.id,
        action="PERMISSION_CHANGE",
        table_name="admin_permissions",
        record_id=target.id,
        detail=f"Mengubah permission admin {target.email}",
        new_data={"permissions": perms},
        ip_address=get_client_ip(request),
    )
    db.commit()
    return success_response(
        data={"id": target.id, "role": target.role, "permissions": perms}
    )

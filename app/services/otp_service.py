import random
from datetime import timedelta

from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.responses import raise_api_error
from app.utils.datetime_utils import utcnow

settings = get_settings()


def generate_otp() -> str:
    return f"{random.randint(0, 999999):06d}"


def otp_expires_at():
    return utcnow() + timedelta(minutes=settings.otp_expire_minutes)


def check_resend_allowed(resend_count: int, last_sent_at) -> None:
    if resend_count >= settings.otp_max_resend:
        raise_api_error("Batas kirim ulang OTP telah tercapai (maksimal 3x).", 429)

    if last_sent_at:
        elapsed = (utcnow() - last_sent_at).total_seconds()
        if elapsed < settings.otp_resend_cooldown_seconds:
            remaining = int(settings.otp_resend_cooldown_seconds - elapsed)
            raise_api_error(f"Tunggu {remaining} detik sebelum meminta OTP baru.", 429)


def verify_otp_code(stored: str, provided: str, expired_at) -> None:
    if utcnow() > expired_at:
        raise_api_error("OTP telah kedaluwarsa. Minta kode baru.", 400)
    if stored != provided.strip():
        raise_api_error("Kode OTP tidak valid.", 400)

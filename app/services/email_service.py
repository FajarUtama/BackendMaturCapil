import logging

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def send_otp_email(to_email: str, otp: str, purpose: str = "verifikasi") -> None:
    subject = f"[MaturCapil] Kode OTP {purpose}"
    body = (
        f"Kode OTP Anda: {otp}\n\n"
        f"Berlaku {settings.otp_expire_minutes} menit.\n"
        "Jangan bagikan kode ini kepada siapapun."
    )

    if not settings.smtp_host:
        logger.info("=== OTP EMAIL (dev mode) ===\nTo: %s\nOTP: %s\n%s", to_email, otp, body)
        return

    import aiosmtplib
    from email.message import EmailMessage

    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    await aiosmtplib.send(
        message,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_user or None,
        password=settings.smtp_password or None,
        start_tls=settings.smtp_tls,
    )

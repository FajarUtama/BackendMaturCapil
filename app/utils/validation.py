import re

from app.core.constants import SEMARANG_LAT_MAX, SEMARANG_LAT_MIN, SEMARANG_LNG_MAX, SEMARANG_LNG_MIN

PASSWORD_PATTERN = re.compile(r"^(?=.*[A-Z])(?=.*\d).{8,}$")
NIK_PATTERN = re.compile(r"^\d{16}$")


def validate_password(password: str) -> list[str]:
    errors = []
    if len(password) < 8:
        errors.append("Password minimal 8 karakter.")
    if not re.search(r"[A-Z]", password):
        errors.append("Password harus mengandung minimal 1 huruf besar.")
    if not re.search(r"\d", password):
        errors.append("Password harus mengandung minimal 1 angka.")
    return errors


def validate_nik(nik: str) -> list[str]:
    errors = []
    if not NIK_PATTERN.match(nik):
        errors.append("NIK harus 16 digit angka.")
    return errors


def is_in_semarang(latitude: float, longitude: float) -> bool:
    return (
        SEMARANG_LAT_MIN <= latitude <= SEMARANG_LAT_MAX
        and SEMARANG_LNG_MIN <= longitude <= SEMARANG_LNG_MAX
    )


def mask_email(email: str) -> str:
    if "@" not in email:
        return email
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        masked_local = local[0] + "******"
    else:
        masked_local = local[:2] + "******"
    return f"{masked_local}@{domain}"


def mask_nik(nik: str) -> str:
    if len(nik) < 8:
        return nik
    return nik[:4] + "*" * (len(nik) - 8) + nik[-4:]

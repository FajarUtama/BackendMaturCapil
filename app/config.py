import os
from functools import lru_cache
from urllib.parse import quote_plus

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_LOCAL_DATABASE_URL = "mysql+pymysql://root@localhost:3306/maturcapil_db?charset=utf8mb4"

# Env yang dipakai Railway / platform lain untuk MySQL
_DATABASE_URL_KEYS = (
    "DATABASE_URL",
    "MYSQL_URL",
    "MYSQL_PUBLIC_URL",
    "MYSQLDATABASE_URL",
)


def _normalize_database_url(url: str) -> str:
    """Railway/MySQL plugin sering memberi mysql:// — SQLAlchemy butuh mysql+pymysql://"""
    if url.startswith("mysql://"):
        return url.replace("mysql://", "mysql+pymysql://", 1)
    return url


def _is_railway() -> bool:
    return bool(os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("RAILWAY_SERVICE_NAME"))


def resolve_database_url() -> str:
    """
    Urutan prioritas:
    1. DATABASE_URL / MYSQL_URL (dari Railway plugin atau manual)
    2. Rakit dari MYSQLHOST, MYSQLPORT, MYSQLUSER, MYSQLPASSWORD, MYSQLDATABASE
    3. Default lokal (development)
    """
    for key in _DATABASE_URL_KEYS:
        raw = os.environ.get(key)
        if raw and raw.strip():
            return _normalize_database_url(raw.strip())

    host = os.environ.get("MYSQLHOST") or os.environ.get("MYSQL_HOST")
    if host:
        port = os.environ.get("MYSQLPORT") or os.environ.get("MYSQL_PORT") or "3306"
        user = os.environ.get("MYSQLUSER") or os.environ.get("MYSQL_USER") or "root"
        password = os.environ.get("MYSQLPASSWORD") or os.environ.get("MYSQL_PASSWORD") or ""
        database = os.environ.get("MYSQLDATABASE") or os.environ.get("MYSQL_DATABASE") or "railway"
        user_q = quote_plus(user)
        if password:
            auth = f"{user_q}:{quote_plus(password)}@"
        else:
            auth = f"{user_q}@"
        return (
            f"mysql+pymysql://{auth}{host}:{port}/{database}?charset=utf8mb4"
        )

    return DEFAULT_LOCAL_DATABASE_URL


def _mask_database_url(url: str) -> str:
    """Sembunyikan password di log."""
    if "@" not in url:
        return url
    try:
        prefix, rest = url.split("://", 1)
        creds, hostpart = rest.split("@", 1)
        if ":" in creds:
            user = creds.split(":", 1)[0]
            return f"{prefix}://{user}:****@{hostpart}"
    except ValueError:
        pass
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "MaturCapil Semarang API"
    app_env: str = "development"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000

    database_url: str = DEFAULT_LOCAL_DATABASE_URL

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_db_url(cls, v: str) -> str:
        return _normalize_database_url(v) if isinstance(v, str) else v

    @model_validator(mode="after")
    def resolve_db_from_platform(self) -> "Settings":
        # Jika .env / env tidak mengisi DATABASE_URL, coba variabel Railway
        env_db = os.environ.get("DATABASE_URL", "").strip()
        if not env_db:
            resolved = resolve_database_url()
            if resolved != self.database_url or "localhost" not in resolved:
                object.__setattr__(self, "database_url", resolved)
        return self

    secret_key: str = "dev-secret-change-in-production"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7
    algorithm: str = "HS256"

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    upload_dir: str = "uploads"
    max_upload_mb: int = 5
    max_complaint_photos: int = 3
    public_base_url: str = "http://localhost:3000"

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@maturcapil.id"
    smtp_tls: bool = True

    otp_expire_minutes: int = 5
    otp_max_resend: int = 3
    otp_resend_cooldown_seconds: int = 60

    login_max_attempts: int = 5
    login_window_minutes: int = 15

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in ("production", "prod") or _is_railway()

    def validate_database_config(self) -> None:
        if "localhost" in self.database_url or "127.0.0.1" in self.database_url:
            if self.is_production:
                raise RuntimeError(
                    "DATABASE_URL belum dikonfigurasi untuk production. "
                    "Di Railway: tambah service MySQL → Variables → Reference ke service backend "
                    "(DATABASE_URL atau MYSQLHOST/MYSQLUSER/...). "
                    "Lihat README bagian Deploy ke Railway."
                )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    # Pastikan URL final memakai resolver (termasuk saat DATABASE_URL kosong di pydantic)
    if not os.environ.get("DATABASE_URL", "").strip():
        resolved = resolve_database_url()
        if resolved != DEFAULT_LOCAL_DATABASE_URL or not settings.is_production:
            object.__setattr__(settings, "database_url", resolved)
    settings.validate_database_config()
    return settings


def get_masked_database_url() -> str:
    return _mask_database_url(get_settings().database_url)

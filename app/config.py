from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "MaturCapil Semarang API"
    app_env: str = "development"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 3000

    database_url: str = "mysql+pymysql://root@localhost:3306/maturcapil_db?charset=utf8mb4"

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


@lru_cache
def get_settings() -> Settings:
    return Settings()

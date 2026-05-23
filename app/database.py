import re
import traceback
from collections.abc import Generator
from urllib.parse import urlparse, urlunparse

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import mask_database_url, resolve_database_url

# Railway MYSQL_URL → mysql:// → mysql+pymysql:// (lihat config.resolve_database_url)
DATABASE_URL = resolve_database_url()

print("DATABASE_URL =", mask_database_url(DATABASE_URL))


def _database_name_from_url(url: str) -> str | None:
    name = urlparse(url).path.lstrip("/").split("?")[0]
    return name or None


def _server_url_without_database(url: str) -> str:
    return urlunparse(urlparse(url)._replace(path="/"))


def ensure_database_exists(url: str) -> None:
    """Buat database jika belum ada (mis. maturcapil_db di Railway MySQL baru)."""
    db_name = _database_name_from_url(url)
    if not db_name or not re.fullmatch(r"[A-Za-z0-9_]+", db_name):
        return

    server_url = _server_url_without_database(url)
    admin = create_engine(server_url, isolation_level="AUTOCOMMIT", pool_pre_ping=True)
    try:
        with admin.connect() as conn:
            conn.execute(
                text(
                    f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
            )
        print(f"DATABASE '{db_name}' READY")
    finally:
        admin.dispose()


ensure_database_exists(DATABASE_URL)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
)

try:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
        print("MYSQL CONNECTION SUCCESS")
except Exception as e:
    print("MYSQL CONNECTION FAILED")
    print(repr(e))
    traceback.print_exc()
    raise


class Base(DeclarativeBase):
    pass


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database_connection() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print("check_database_connection failed:", repr(e))
        traceback.print_exc()
        return False

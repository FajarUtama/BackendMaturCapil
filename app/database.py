import os
import traceback
from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL") or ""

# Railway kasih mysql://
# SQLAlchemy PyMySQL butuh mysql+pymysql://
if DATABASE_URL.startswith("mysql://"):
    DATABASE_URL = DATABASE_URL.replace("mysql://", "mysql+pymysql://", 1)

if not DATABASE_URL:
    DATABASE_URL = "mysql+pymysql://root@localhost:3306/maturcapil_db?charset=utf8mb4"

print("DATABASE_URL =", DATABASE_URL)

_connect_args: dict = {}
if os.getenv("MYSQL_SSL", "").lower() in ("1", "true", "yes"):
    _connect_args["ssl"] = {"ssl_mode": "REQUIRED"}

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args=_connect_args or {},
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

import traceback
from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import mask_database_url, resolve_database_url

# Railway MYSQL_URL → mysql:// → mysql+pymysql:// (lihat config.resolve_database_url)
DATABASE_URL = resolve_database_url()

print("DATABASE_URL =", mask_database_url(DATABASE_URL))

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

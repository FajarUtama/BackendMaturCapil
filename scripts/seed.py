"""Jalankan: python -m scripts.seed (dari root project)"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.constants import ALL_PERMISSION_CODES, CITIZEN_ROLE
from app.core.security import hash_password
from app.database import Base, SessionLocal, engine
from app.models.category import Category
from app.models.permission import AdminPermission, Permission
from app.models.user import User
from app.services.permissions import ensure_permissions_exist, set_admin_permissions
from app.utils.datetime_utils import utcnow
from app.utils.ids import new_id

DEMO_PASSWORD = "Password1"


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        ensure_permissions_exist(db)

        categories = [
            ("ktp", "KTP-el", "KTP", "Pengaduan KTP elektronik"),
            ("jalan", "Jalan Rusak", "JALAN", "Kerusakan jalan dan permukaan"),
            ("sampah", "Sampah", "SAMPAH", "Pengelolaan sampah"),
            ("lampu", "Lampu Jalan", "LAMPU", "Penerangan jalan umum"),
            ("drainase", "Drainase", "DRAIN", "Saluran air dan banjir"),
            ("pelayanan", "Pelayanan Publik", "LAYANAN", "Pelayanan administrasi"),
            ("infra", "Infrastruktur", "INFRA", "Fasilitas umum"),
            ("lainnya", "Lainnya", "LAIN", "Kategori lainnya"),
        ]
        for cat_id, name, code, desc in categories:
            if not db.query(Category).filter(Category.id == cat_id).first():
                db.add(
                    Category(
                        id=cat_id,
                        name=name,
                        code=code,
                        description=desc,
                        is_active=True,
                    )
                )

        def upsert_user(email: str, name: str, role: str, nik: str, perms: list[str] | None = None):
            email_l = email.lower()
            user = db.query(User).filter(User.email == email_l).first()
            if not user:
                user = User(
                    id=new_id("usr"),
                    name=name,
                    email=email_l,
                    nik=nik,
                    password_hash=hash_password(DEMO_PASSWORD),
                    role=role,
                    status="ACTIVE",
                    email_verified_at=utcnow(),
                )
                db.add(user)
                db.flush()
            else:
                user.password_hash = hash_password(DEMO_PASSWORD)
                user.status = "ACTIVE"
                user.deleted_at = None

            if role == "Admin" and perms is not None:
                set_admin_permissions(db, user, perms)
            return user

        upsert_user(
            "citizen@maturcapil.id",
            "Budi Santoso",
            CITIZEN_ROLE,
            "3374012345678901",
        )
        upsert_user(
            "superadmin@maturcapil.id",
            "Super Admin",
            "Super Admin",
            "3374023456789012",
        )
        upsert_user(
            "admin@maturcapil.id",
            "Siti Aminah",
            "Admin",
            "3374034567890123",
            [
                "dashboard.view",
                "complaint.verify",
                "complaint.reject",
                "complaint.close",
                "complaint.export",
                "user.view",
                "category.manage",
                "auditlog.view",
            ],
        )
        upsert_user(
            "amir@maturcapil.id",
            "Admin Amir",
            "Admin",
            "3374045678901234",
            ["dashboard.view", "complaint.verify", "complaint.reject"],
        )

        db.commit()
        print("Seed selesai. Akun demo (password: Password1):")
        print("  - citizen@maturcapil.id (Masyarakat)")
        print("  - admin@maturcapil.id (Admin)")
        print("  - superadmin@maturcapil.id (Super Admin)")
        print("  - amir@maturcapil.id (Admin terbatas)")
    finally:
        db.close()


if __name__ == "__main__":
    seed()

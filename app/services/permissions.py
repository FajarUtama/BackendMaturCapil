from sqlalchemy.orm import Session, joinedload

from app.core.constants import ALL_PERMISSION_CODES, CITIZEN_ROLE
from app.models.permission import AdminPermission, Permission
from app.models.user import User


def get_user_permission_codes(db: Session, user: User) -> list[str]:
    if user.role == "Super Admin":
        return list(ALL_PERMISSION_CODES)
    if user.role != "Admin":
        return []
    db.refresh(user)
    codes = (
        db.query(Permission.code)
        .join(AdminPermission, AdminPermission.permission_id == Permission.id)
        .filter(AdminPermission.admin_id == user.id)
        .all()
    )
    return [c[0] for c in codes]


def user_has_permission(db: Session, user: User, code: str) -> bool:
    if user.role == "Super Admin":
        return True
    if user.role != "Admin":
        return False
    return code in get_user_permission_codes(db, user)


def set_admin_permissions(db: Session, admin: User, permission_codes: list[str]) -> list[str]:
    db.query(AdminPermission).filter(AdminPermission.admin_id == admin.id).delete()
    valid_codes = [c for c in permission_codes if c in ALL_PERMISSION_CODES]
    perms = db.query(Permission).filter(Permission.code.in_(valid_codes)).all()
    for perm in perms:
        from app.utils.ids import new_id

        db.add(
            AdminPermission(
                id=new_id("ap"),
                admin_id=admin.id,
                permission_id=perm.id,
            )
        )
    db.flush()
    return get_user_permission_codes(db, admin)


def ensure_permissions_exist(db: Session) -> None:
    from app.utils.ids import new_id

    existing = {p.code for p in db.query(Permission).all()}
    for code in ALL_PERMISSION_CODES:
        if code not in existing:
            db.add(
                Permission(
                    id=new_id("perm"),
                    name=code.replace(".", " ").title(),
                    code=code,
                    description=None,
                )
            )
    db.commit()

from sqlalchemy.orm import Session, joinedload

from app.models.permission import AdminPermission
from app.models.user import User
from app.services.permissions import get_user_permission_codes
from app.utils.datetime_utils import to_iso
from app.utils.validation import mask_email, mask_nik


def serialize_user(
    user: User,
    db: Session,
    *,
    mask_sensitive: bool = False,
    include_permissions: bool = True,
) -> dict:
    nik = user.nik or ""
    email = user.email
    if mask_sensitive:
        nik = mask_nik(nik) if nik else ""
        email = mask_email(email)

    data = {
        "id": user.id,
        "name": user.name,
        "email": email,
        "role": user.role,
        "nik": nik,
        "status": user.status,
        "email_verified": user.email_verified,
        "email_verified_at": to_iso(user.email_verified_at),
        "created_at": to_iso(user.created_at),
        "deleted_at": to_iso(user.deleted_at),
        "deleted_by": user.deleted_by,
    }
    if include_permissions:
        data["permissions"] = get_user_permission_codes(db, user) if user.role != "Masyarakat" else []
    return data

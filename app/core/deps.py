from typing import Annotated

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.constants import ADMIN_ROLES, CITIZEN_ROLE
from app.core.responses import raise_api_error
from app.core.security import decode_access_token
from app.database import get_db
from app.models.user import User
from app.services.permissions import user_has_permission

security = HTTPBearer(auto_error=False)


def get_client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def get_current_user_optional(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> User | None:
    if not credentials:
        return None
    payload = decode_access_token(credentials.credentials)
    if not payload:
        return None
    user = db.query(User).filter(User.id == payload.get("sub"), User.deleted_at.is_(None)).first()
    return user


def get_current_user(user: User | None = Depends(get_current_user_optional)) -> User:
    if not user:
        raise_api_error("Token tidak valid atau telah kedaluwarsa.", 401)
    if user.status == "SUSPENDED":
        raise_api_error("Akun ditangguhkan.", 403)
    if user.status == "INACTIVE":
        raise_api_error("Akun dinonaktifkan.", 403)
    return user


def require_citizen(user: User = Depends(get_current_user)) -> User:
    if user.role != CITIZEN_ROLE:
        raise_api_error("Gunakan Portal Warga.", 403)
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role not in ADMIN_ROLES:
        raise_api_error("Gunakan Portal Admin.", 403)
    return user


def require_permission(code: str):
    def checker(
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        if user.role == "Super Admin":
            return user
        if user.role != "Admin" or not user_has_permission(db, user, code):
            raise_api_error("Anda tidak memiliki izin untuk aksi ini.", 403)
        return user

    return checker


def require_super_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "Super Admin":
        raise_api_error("Hanya Super Admin yang dapat melakukan aksi ini.", 403)
    return user

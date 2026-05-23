from datetime import timedelta

from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token_value,
    hash_token,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.services.user_service import serialize_user
from app.utils.datetime_utils import utcnow
from app.utils.ids import new_id

settings = get_settings()


def issue_tokens(db: Session, user: User) -> dict:
    access = create_access_token(user.id)
    refresh_value = create_refresh_token_value()
    refresh = RefreshToken(
        id=new_id("rt"),
        user_id=user.id,
        token_hash=hash_token(refresh_value),
        expires_at=utcnow() + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(refresh)
    db.flush()
    return {
        "access_token": access,
        "refresh_token": refresh_value,
        "token_type": "Bearer",
        "expires_in": settings.access_token_expire_minutes * 60,
        "user": serialize_user(user, db),
    }


def revoke_refresh_tokens(db: Session, user_id: str) -> None:
    tokens = (
        db.query(RefreshToken)
        .filter(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .all()
    )
    now = utcnow()
    for t in tokens:
        t.revoked_at = now

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.constants import ADMIN_ROLES, CITIZEN_ROLE
from app.core.deps import get_client_ip, get_current_user, require_permission
from app.core.responses import raise_api_error, success_response
from app.database import get_db
from app.models.category import Category
from app.models.user import User
from app.schemas.category import CategoryCreateRequest, CategoryUpdateRequest
from app.services.audit import write_audit_log
from app.utils.datetime_utils import to_iso, utcnow
from app.utils.ids import new_id, slugify_code

router = APIRouter(prefix="/categories", tags=["Kategori"])


def _serialize_category(cat: Category) -> dict:
    return {
        "id": cat.id,
        "name": cat.name,
        "code": cat.code,
        "description": cat.description or "",
        "is_active": cat.is_active,
        "deleted_at": to_iso(cat.deleted_at),
        "deleted_by": cat.deleted_by,
    }


@router.get("")
def list_categories(
    include_inactive: bool = False,
    active_only: bool = False,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Category).filter(Category.deleted_at.is_(None))
    if user.role == CITIZEN_ROLE or active_only:
        q = q.filter(Category.is_active.is_(True))
    elif not include_inactive and user.role in ADMIN_ROLES:
        pass
    elif user.role in ADMIN_ROLES and include_inactive:
        pass
    else:
        q = q.filter(Category.is_active.is_(True))

    cats = q.order_by(Category.name).all()
    return success_response(data=[_serialize_category(c) for c in cats])


@router.post("")
def create_category(
    body: CategoryCreateRequest,
    request: Request,
    user: User = Depends(require_permission("category.manage")),
    db: Session = Depends(get_db),
):
    code = body.code.strip().upper()
    cat_id = slugify_code(body.code)
    if db.query(Category).filter((Category.id == cat_id) | (Category.code == code)).first():
        raise_api_error("Kode kategori sudah digunakan.", 400)

    cat = Category(
        id=cat_id,
        name=body.name.strip(),
        code=code,
        description=body.description,
        is_active=True,
    )
    db.add(cat)
    write_audit_log(
        db,
        user_id=user.id,
        action="CREATE_CATEGORY",
        table_name="categories",
        record_id=cat.id,
        detail=f"Membuat kategori {cat.name}",
        ip_address=get_client_ip(request),
    )
    db.commit()
    return success_response(data=_serialize_category(cat), status_code=201)


@router.patch("/{category_id}")
def update_category(
    category_id: str,
    body: CategoryUpdateRequest,
    request: Request,
    user: User = Depends(require_permission("category.manage")),
    db: Session = Depends(get_db),
):
    cat = db.query(Category).filter(Category.id == category_id, Category.deleted_at.is_(None)).first()
    if not cat:
        raise_api_error("Kategori tidak ditemukan.", 404)

    if body.name is not None:
        cat.name = body.name.strip()
    if body.code is not None:
        cat.code = body.code.strip().upper()
    if body.description is not None:
        cat.description = body.description
    if body.is_active is not None:
        cat.is_active = body.is_active

    write_audit_log(
        db,
        user_id=user.id,
        action="UPDATE_CATEGORY",
        table_name="categories",
        record_id=cat.id,
        detail=f"Memperbarui kategori {cat.name}",
        ip_address=get_client_ip(request),
    )
    db.commit()
    return success_response(data=_serialize_category(cat))


@router.delete("/{category_id}")
def delete_category(
    category_id: str,
    request: Request,
    user: User = Depends(require_permission("category.manage")),
    db: Session = Depends(get_db),
):
    cat = db.query(Category).filter(Category.id == category_id, Category.deleted_at.is_(None)).first()
    if not cat:
        raise_api_error("Kategori tidak ditemukan.", 404)

    cat.is_active = False
    cat.deleted_at = utcnow()
    cat.deleted_by = user.id
    write_audit_log(
        db,
        user_id=user.id,
        action="DELETE_CATEGORY",
        table_name="categories",
        record_id=cat.id,
        detail=f"Menonaktifkan kategori {cat.name}",
        ip_address=get_client_ip(request),
    )
    db.commit()
    return success_response(message="Kategori dinonaktifkan")

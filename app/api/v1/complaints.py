from fastapi import APIRouter, Depends, Request, UploadFile
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.core.constants import ADMIN_ROLES, CITIZEN_ROLE, COMPLAINT_STATUSES, PRIORITIES
from app.core.deps import get_client_ip, get_current_user, require_permission
from app.core.responses import raise_api_error, success_response
from app.database import get_db
from app.models.complaint import Complaint, ComplaintFile, ComplaintStatusLog
from app.models.user import User
from app.schemas.complaint import ChatCreateRequest, ComplaintCloseRequest, ComplaintStatusUpdate
from app.services.audit import write_audit_log
from app.services.complaint_service import (
    add_status_log,
    generate_ticket_number,
    serialize_complaint,
)
from app.services.file_service import public_url, save_complaint_image
from app.services.permissions import user_has_permission
from app.utils.datetime_utils import to_iso, utcnow
from app.utils.ids import new_id
from app.utils.validation import is_in_semarang

router = APIRouter(prefix="/complaints", tags=["Pengaduan"])
settings = get_settings()


def _get_complaint_or_404(db: Session, complaint_id: str) -> Complaint:
    complaint = (
        db.query(Complaint)
        .options(joinedload(Complaint.user), joinedload(Complaint.files))
        .filter(Complaint.id == complaint_id)
        .first()
    )
    if not complaint:
        raise_api_error("Laporan tidak ditemukan.", 404)
    return complaint


def _can_access_complaint(user: User, complaint: Complaint, db: Session) -> bool:
    if user.role in ADMIN_ROLES:
        return user.role == "Super Admin" or user_has_permission(db, user, "dashboard.view") or True
    return complaint.user_id == user.id


@router.get("")
def list_complaints(
    user_id: str | None = None,
    status: str | None = None,
    category_id: str | None = None,
    priority: str | None = None,
    search: str | None = None,
    page: int = 1,
    per_page: int = 20,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Complaint).options(joinedload(Complaint.user), joinedload(Complaint.files))

    if user.role == CITIZEN_ROLE:
        q = q.filter(Complaint.user_id == user.id)
    elif user_id:
        q = q.filter(Complaint.user_id == user_id)

    if status:
        q = q.filter(Complaint.status == status)
    if category_id:
        q = q.filter(Complaint.category_id == category_id)
    if priority:
        q = q.filter(Complaint.priority == priority)
    if search:
        term = f"%{search}%"
        q = q.join(Complaint.user).filter(
            or_(
                Complaint.title.ilike(term),
                Complaint.ticket_number.ilike(term),
                Complaint.description.ilike(term),
                User.name.ilike(term),
            )
        )

    total = q.count()
    page = max(1, page)
    per_page = min(max(1, per_page), 100)
    items = (
        q.order_by(Complaint.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    return success_response(
        data={
            "items": [serialize_complaint(c) for c in items],
            "meta": {"page": page, "per_page": per_page, "total": total},
        }
    )


@router.get("/{complaint_id}")
def get_complaint(
    complaint_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    complaint = _get_complaint_or_404(db, complaint_id)
    if not _can_access_complaint(user, complaint, db) and complaint.user_id != user.id:
        if user.role not in ADMIN_ROLES:
            raise_api_error("Akses ditolak.", 403)
    return success_response(data=serialize_complaint(complaint))


@router.post("")
async def create_complaint(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role != CITIZEN_ROLE:
        raise_api_error("Hanya masyarakat yang dapat membuat laporan.", 403)

    content_type = request.headers.get("content-type", "")
    photos_urls: list[str] = []
    upload_files: list[UploadFile] = []

    if "multipart/form-data" in content_type:
        form = await request.form()
        title = str(form.get("title", "")).strip()
        description = str(form.get("description", "")).strip()
        category_id = str(form.get("category_id", "")).strip()
        priority = str(form.get("priority", "Sedang")).strip()
        try:
            latitude = float(form.get("latitude", 0))
            longitude = float(form.get("longitude", 0))
        except (TypeError, ValueError):
            raise_api_error("Koordinat tidak valid.", 400)
        address = str(form.get("address", "")).strip()
        for key in form:
            if key.startswith("photos"):
                val = form[key]
                if hasattr(val, "read"):
                    upload_files.append(val)
    else:
        body = await request.json()
        title = body.get("title", "").strip()
        description = body.get("description", "").strip()
        category_id = body.get("category_id", "").strip()
        priority = body.get("priority", "Sedang")
        latitude = float(body.get("latitude", 0))
        longitude = float(body.get("longitude", 0))
        address = body.get("address", "").strip()
        photos_urls = body.get("photos") or []

    if not title or not description or not category_id or not address:
        raise_api_error("Data laporan tidak lengkap.", 400)
    if priority not in PRIORITIES:
        raise_api_error("Prioritas tidak valid.", 400)
    if not is_in_semarang(latitude, longitude):
        raise_api_error("Lokasi harus berada di wilayah Kota Semarang.", 400)

    if not user.email_verified:
        count = db.query(Complaint).filter(Complaint.user_id == user.id).count()
        if count >= 1:
            return error_response(
                "Anda hanya dapat membuat 1 laporan sebelum email diverifikasi.",
                status_code=403,
                needs_email_verification=True,
            )

    if len(upload_files) > settings.max_complaint_photos:
        raise_api_error(f"Maksimal {settings.max_complaint_photos} foto.", 400)

    ticket = generate_ticket_number(db)
    complaint = Complaint(
        id=new_id("comp"),
        ticket_number=ticket,
        user_id=user.id,
        title=title,
        description=description,
        category_id=category_id,
        status="Menunggu Verifikasi",
        priority=priority,
        latitude=latitude,
        longitude=longitude,
        address=address,
    )
    db.add(complaint)
    db.flush()

    for f in upload_files:
        path = await save_complaint_image(f)
        db.add(
            ComplaintFile(
                id=new_id("cf"),
                complaint_id=complaint.id,
                file_path=path,
                file_type="evidence",
            )
        )

    for url in photos_urls:
        if isinstance(url, str) and url.startswith("http"):
            rel = url.split("/uploads/")[-1] if "/uploads/" in url else url
            db.add(
                ComplaintFile(
                    id=new_id("cf"),
                    complaint_id=complaint.id,
                    file_path=rel,
                    file_type="evidence",
                )
            )

    add_status_log(
        db,
        complaint,
        "Menunggu Verifikasi",
        "Aduan berhasil diajukan oleh masyarakat.",
        user.id,
    )
    db.commit()
    db.refresh(complaint)
    return success_response(
        data={
            "id": complaint.id,
            "ticket_number": complaint.ticket_number,
            "status": complaint.status,
            "created_at": to_iso(complaint.created_at),
        },
        message="Aduan berhasil dikirim",
        status_code=201,
    )


@router.patch("/{complaint_id}/status")
def update_complaint_status(
    complaint_id: str,
    body: ComplaintStatusUpdate,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.status not in COMPLAINT_STATUSES:
        raise_api_error("Status tidak valid.", 400)

    if body.status == "Ditolak":
        if user.role != "Super Admin" and not user_has_permission(db, user, "complaint.reject"):
            raise_api_error("Anda tidak memiliki izin untuk menolak laporan.", 403)
    elif body.status in ("Diproses", "Menunggu Verifikasi"):
        if user.role != "Super Admin" and not user_has_permission(db, user, "complaint.verify"):
            raise_api_error("Anda tidak memiliki izin untuk verifikasi laporan.", 403)
    else:
        if user.role != "Super Admin" and not user_has_permission(db, user, "complaint.verify"):
            raise_api_error("Anda tidak memiliki izin.", 403)

    complaint = _get_complaint_or_404(db, complaint_id)
    old_status = complaint.status
    complaint.status = body.status
    add_status_log(db, complaint, body.status, body.note, user.id)

    action = "UPDATE_STATUS"
    if body.status == "Diproses" and old_status == "Menunggu Verifikasi":
        action = "VERIFY_COMPLAINT"
    elif body.status == "Ditolak":
        action = "REJECT_COMPLAINT"

    write_audit_log(
        db,
        user_id=user.id,
        action=action,
        table_name="complaints",
        record_id=complaint.id,
        detail=body.note or f"Status diubah ke {body.status}",
        ip_address=get_client_ip(request),
    )
    db.commit()
    return success_response(data=serialize_complaint(complaint))


@router.post("/{complaint_id}/close")
async def close_complaint(
    complaint_id: str,
    request: Request,
    body: ComplaintCloseRequest | None = None,
    user: User = Depends(require_permission("complaint.close")),
    db: Session = Depends(get_db),
):
    complaint = _get_complaint_or_404(db, complaint_id)
    resolution_note = ""
    evidence_urls: list[str] = []

    content_type = request.headers.get("content-type", "")
    if body is not None:
        resolution_note = body.resolution_note.strip()
        evidence_urls = body.evidence_after_photos or []
    elif "multipart/form-data" in content_type:
        form = await request.form()
        resolution_note = str(form.get("resolution_note", "")).strip()
        for key in form:
            if key.startswith("evidence"):
                val = form[key]
                if hasattr(val, "read"):
                    path = await save_complaint_image(val, "evidence_after")
                    db.add(
                        ComplaintFile(
                            id=new_id("cf"),
                            complaint_id=complaint.id,
                            file_path=path,
                            file_type="after",
                        )
                    )
    else:
        raw = await request.json()
        resolution_note = (raw.get("resolution_note") or "").strip()
        evidence_urls = raw.get("evidence_after_photos") or []

    if not resolution_note:
        raise_api_error("Catatan penyelesaian wajib diisi.", 400)

    for url in evidence_urls or []:
        if isinstance(url, str):
            rel = url.split("/uploads/")[-1] if "/uploads/" in url else url
            db.add(
                ComplaintFile(
                    id=new_id("cf"),
                    complaint_id=complaint.id,
                    file_path=rel,
                    file_type="after",
                )
            )

    now = utcnow()
    complaint.status = "Selesai"
    complaint.resolution_note = resolution_note
    complaint.resolved_at = now
    add_status_log(db, complaint, "Selesai", resolution_note, user.id)
    write_audit_log(
        db,
        user_id=user.id,
        action="CLOSE_COMPLAINT",
        table_name="complaints",
        record_id=complaint.id,
        detail=resolution_note,
        ip_address=get_client_ip(request),
    )
    db.commit()
    db.refresh(complaint)
    return success_response(data=serialize_complaint(complaint))


@router.get("/{complaint_id}/status-logs")
def list_status_logs(
    complaint_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    complaint = _get_complaint_or_404(db, complaint_id)
    if user.role == CITIZEN_ROLE and complaint.user_id != user.id:
        raise_api_error("Akses ditolak.", 403)

    logs = (
        db.query(ComplaintStatusLog)
        .options(joinedload(ComplaintStatusLog.changer))
        .filter(ComplaintStatusLog.complaint_id == complaint_id)
        .order_by(ComplaintStatusLog.created_at.asc())
        .all()
    )
    data = [
        {
            "id": log.id,
            "complaint_id": log.complaint_id,
            "status": log.status,
            "note": log.note,
            "changed_by": log.changer.name if log.changer else "Sistem",
            "created_at": to_iso(log.created_at),
        }
        for log in logs
    ]
    return success_response(data=data)


@router.get("/{complaint_id}/chats")
def list_chats(
    complaint_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    complaint = _get_complaint_or_404(db, complaint_id)
    if user.role == CITIZEN_ROLE and complaint.user_id != user.id:
        raise_api_error("Akses ditolak.", 403)

    from app.models.chat import Chat

    chats = (
        db.query(Chat)
        .options(joinedload(Chat.sender))
        .filter(Chat.complaint_id == complaint_id)
        .order_by(Chat.created_at.asc())
        .all()
    )
    return success_response(
        data=[
            {
                "id": c.id,
                "complaint_id": c.complaint_id,
                "sender_id": c.sender_id,
                "sender_name": c.sender.name if c.sender else "",
                "message": c.message,
                "created_at": to_iso(c.created_at),
            }
            for c in chats
        ]
    )


@router.post("/{complaint_id}/chats")
def send_chat(
    complaint_id: str,
    body: ChatCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    complaint = _get_complaint_or_404(db, complaint_id)
    if user.role == CITIZEN_ROLE and complaint.user_id != user.id:
        raise_api_error("Akses ditolak.", 403)

    from app.models.chat import Chat

    chat = Chat(
        id=new_id("chat"),
        complaint_id=complaint_id,
        sender_id=user.id,
        message=body.message.strip(),
    )
    db.add(chat)
    db.commit()
    db.refresh(chat)
    return success_response(
        data={
            "id": chat.id,
            "complaint_id": chat.complaint_id,
            "sender_id": chat.sender_id,
            "sender_name": user.name,
            "message": chat.message,
            "created_at": to_iso(chat.created_at),
        },
        status_code=201,
    )

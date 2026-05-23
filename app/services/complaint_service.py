from datetime import datetime

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.models.category import Category
from app.models.complaint import Complaint, ComplaintFile, ComplaintStatusLog
from app.models.user import User
from app.services.file_service import public_url
from app.utils.datetime_utils import to_iso
from app.utils.ids import new_id


def generate_ticket_number(db: Session) -> str:
    year = datetime.now().year
    prefix = f"TKT-{year}-"
    last = (
        db.query(Complaint.ticket_number)
        .filter(Complaint.ticket_number.like(f"{prefix}%"))
        .order_by(Complaint.ticket_number.desc())
        .first()
    )
    if last:
        try:
            num = int(last[0].split("-")[-1]) + 1
        except ValueError:
            num = 1
    else:
        num = 1
    return f"{prefix}{num:04d}"


def get_complaint_photos(complaint: Complaint, file_type: str = "evidence") -> list[str]:
    return [public_url(f.file_path) for f in complaint.files if f.file_type == file_type]


def serialize_complaint(complaint: Complaint, user_name: str | None = None) -> dict:
    name = user_name or (complaint.user.name if complaint.user else None)
    return {
        "id": complaint.id,
        "ticket_number": complaint.ticket_number,
        "user_id": complaint.user_id,
        "user_name": name,
        "title": complaint.title,
        "description": complaint.description,
        "category_id": complaint.category_id,
        "status": complaint.status,
        "priority": complaint.priority,
        "latitude": complaint.latitude,
        "longitude": complaint.longitude,
        "address": complaint.address,
        "created_at": to_iso(complaint.created_at),
        "photos": get_complaint_photos(complaint, "evidence"),
        "evidence_after_photos": get_complaint_photos(complaint, "after"),
        "resolution_note": complaint.resolution_note or "",
        "resolved_at": to_iso(complaint.resolved_at),
    }


def add_status_log(
    db: Session,
    complaint: Complaint,
    status: str,
    note: str | None,
    changed_by_id: str,
) -> ComplaintStatusLog:
    log = ComplaintStatusLog(
        id=new_id("log"),
        complaint_id=complaint.id,
        status=status,
        note=note,
        changed_by=changed_by_id,
    )
    db.add(log)
    return log

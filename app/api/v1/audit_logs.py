import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.deps import require_permission
from app.core.responses import success_response
from app.database import get_db
from app.models.audit_log import AuditLog
from app.models.user import User
from app.utils.datetime_utils import to_iso

router = APIRouter(prefix="/audit-logs", tags=["Audit Log"])


def _serialize_log(log: AuditLog, user_name: str | None = None) -> dict:
    return {
        "id": log.id,
        "user_id": log.user_id,
        "user_name": user_name or "",
        "action": log.action,
        "table_name": log.table_name,
        "record_id": log.record_id,
        "detail": log.detail,
        "ip_address": log.ip_address,
        "created_at": to_iso(log.created_at),
    }


@router.get("")
def list_audit_logs(
    action: str | None = None,
    search: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = 1,
    per_page: int = 20,
    user: User = Depends(require_permission("auditlog.view")),
    db: Session = Depends(get_db),
):
    q = db.query(AuditLog)
    if action:
        q = q.filter(AuditLog.action == action)
    if date_from:
        q = q.filter(AuditLog.created_at >= datetime.fromisoformat(date_from.replace("Z", "+00:00")))
    if date_to:
        q = q.filter(AuditLog.created_at <= datetime.fromisoformat(date_to.replace("Z", "+00:00")))
    if search:
        term = f"%{search}%"
        q = q.filter(
            or_(
                AuditLog.detail.ilike(term),
                AuditLog.record_id.ilike(term),
                AuditLog.ip_address.ilike(term),
            )
        )

    total = q.count()
    page = max(1, page)
    per_page = min(max(1, per_page), 100)
    logs = q.order_by(AuditLog.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    user_ids = {log.user_id for log in logs if log.user_id}
    names = {}
    if user_ids:
        for u in db.query(User).filter(User.id.in_(user_ids)).all():
            names[u.id] = u.name

    return success_response(
        data={
            "items": [_serialize_log(log, names.get(log.user_id)) for log in logs],
            "meta": {"page": page, "per_page": per_page, "total": total},
        }
    )


@router.get("/export")
def export_audit_logs(
    action: str | None = None,
    search: str | None = None,
    user: User = Depends(require_permission("auditlog.view")),
    db: Session = Depends(get_db),
):
    q = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(5000)
    if action:
        q = q.filter(AuditLog.action == action)

    logs = q.all()
    user_ids = {log.user_id for log in logs if log.user_id}
    names = {u.id: u.name for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID Log", "Petugas", "Aksi", "Tabel", "ID Record", "IP", "Keterangan", "Waktu"])
    for log in logs:
        writer.writerow(
            [
                log.id,
                names.get(log.user_id, ""),
                log.action,
                log.table_name or "",
                log.record_id or "",
                log.ip_address or "",
                log.detail or "",
                to_iso(log.created_at) or "",
            ]
        )

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit-logs.csv"},
    )

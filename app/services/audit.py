import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.utils.ids import new_id


def write_audit_log(
    db: Session,
    *,
    user_id: str | None,
    action: str,
    table_name: str | None = None,
    record_id: str | None = None,
    detail: str | None = None,
    old_data: Any = None,
    new_data: Any = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    log = AuditLog(
        id=new_id("audit"),
        user_id=user_id,
        action=action,
        table_name=table_name,
        record_id=record_id,
        detail=detail,
        old_data=json.dumps(old_data, default=str) if old_data is not None else None,
        new_data=json.dumps(new_data, default=str) if new_data is not None else None,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(log)
    db.flush()
    return log

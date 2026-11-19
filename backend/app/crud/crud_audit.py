from typing import Optional
from sqlalchemy.orm import Session
from app.db.models.audit_log import AuditLog

def log_audit(
    db: Session,
    action: str,
    details: Optional[str] = None,
    user_id: Optional[int] = None,
    user_email: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> AuditLog:
    log_entry = AuditLog(
        action=action,
        details=details,
        user_id=user_id,
        user_email=user_email,
        ip_address=ip_address,
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return log_entry

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime
from app.db.base import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, nullable=True)
    user_email = Column(String(120), nullable=True, index=True)
    action = Column(String(50), nullable=False, index=True)  # LOGIN, LOGOUT, INTAKE_CREATED, RX_COMPLETED, RX_DISPENSED, RX_DELETED
    details = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

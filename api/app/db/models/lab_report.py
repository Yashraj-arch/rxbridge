from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.db.base import Base

class LabReport(Base):
    __tablename__ = "lab_reports"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    patient_mobile = Column(String(15), ForeignKey("patients.mobile", ondelete="CASCADE"), index=True, nullable=False)
    file_name = Column(String(255), nullable=False)
    file_url = Column(Text, nullable=False)
    public_id = Column(String(255), nullable=True)  # Cloudinary public ID if applicable
    uploaded_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    uploaded_by_email = Column(String(120), nullable=True)
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    patient_rel = relationship("Patient", back_populates="lab_reports")

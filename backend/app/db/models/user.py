from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.enums import UserRole

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(120), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default=UserRole.DOCTOR.value, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Doctor letterhead / clinic settings (stored per doctor, matching BRD Section 9.2)
    doctor_name = Column(String(150), nullable=True)
    reg_no = Column(String(100), nullable=True)
    qualification = Column(String(150), nullable=True)
    clinic_name = Column(String(200), nullable=True)
    clinic_address = Column(String(300), nullable=True)
    clinic_phone = Column(String(50), nullable=True)
    signature_data = Column(Text, nullable=True)  # Base64 PNG signature

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    prescriptions = relationship("Prescription", back_populates="doctor", foreign_keys="Prescription.doctor_id")
    created_prescriptions = relationship("Prescription", back_populates="created_by", foreign_keys="Prescription.created_by_id")

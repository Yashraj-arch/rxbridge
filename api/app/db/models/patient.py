from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from sqlalchemy.orm import relationship
from app.db.base import Base

class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    mobile = Column(String(15), unique=True, index=True, nullable=False)
    name = Column(String(150), nullable=False)
    age_gender = Column(String(50), nullable=False)
    weight = Column(Float, nullable=True)
    height = Column(Float, nullable=True)

    # Consent preferences (latest recorded consent per mobile, as per BRD 6.6)
    consent_offers = Column(Boolean, default=False, nullable=False)
    consent_refill = Column(Boolean, default=False, nullable=False)
    last_consent_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    prescriptions = relationship("Prescription", back_populates="patient_rel")
    lab_reports = relationship("LabReport", back_populates="patient_rel")

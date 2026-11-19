from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.enums import PrescriptionStatus

class Prescription(Base):
    __tablename__ = "prescriptions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    rx_number = Column(String(50), unique=True, index=True, nullable=False)
    
    # Patient info
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="SET NULL"), nullable=True)
    patient_name = Column(String(150), nullable=False)
    patient_mobile = Column(String(15), index=True, nullable=False)
    patient_age_gender = Column(String(50), nullable=False)
    patient_weight = Column(Float, nullable=True)

    # Diagnosis / Chief Complaint
    diagnosis = Column(Text, nullable=True)

    # Vitals
    bp_sys = Column(Integer, nullable=True)
    bp_dia = Column(Integer, nullable=True)
    pulse = Column(Integer, nullable=True)
    temperature = Column(Float, nullable=True)
    spo2 = Column(Integer, nullable=True)
    respiratory_rate = Column(Integer, nullable=True)
    height = Column(Float, nullable=True)
    bmi = Column(Float, nullable=True)
    blood_sugar = Column(Integer, nullable=True)
    sugar_type = Column(String(30), nullable=True)  # Random / Fasting / Post-meal

    # Advice & Follow-up
    advice = Column(Text, nullable=True)
    follow_up_date = Column(String(50), nullable=True)

    # Status: intake -> completed -> dispensed
    status = Column(String(20), default=PrescriptionStatus.INTAKE.value, nullable=False, index=True)

    # Consent (as per BRD 6.6)
    consent_offers = Column(Boolean, default=False, nullable=False, index=True)
    consent_refill = Column(Boolean, default=False, nullable=False)
    consent_recorded_by = Column(String(120), nullable=True)
    consent_recorded_at = Column(DateTime, nullable=True)

    # Doctor and Staff references
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_by_email = Column(String(120), nullable=True)
    doctor_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    doctor_email = Column(String(120), nullable=True)

    # Doctor letterhead snapshot at issue time (frozen, as required by BRD 6.4 FR-4.8)
    doctor_info = Column(JSON, nullable=True)

    # Dispensing info
    dispensed_at = Column(DateTime, nullable=True)
    dispensed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    patient_rel = relationship("Patient", back_populates="prescriptions")
    doctor = relationship("User", back_populates="prescriptions", foreign_keys=[doctor_id])
    created_by = relationship("User", back_populates="created_prescriptions", foreign_keys=[created_by_id])
    medicines = relationship("PrescriptionMedicine", back_populates="prescription", cascade="all, delete-orphan", order_by="PrescriptionMedicine.order_index")

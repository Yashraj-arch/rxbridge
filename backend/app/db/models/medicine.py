from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, JSON, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.db.base import Base

class PrescriptionMedicine(Base):
    __tablename__ = "prescription_medicines"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    prescription_id = Column(Integer, ForeignKey("prescriptions.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    dose = Column(String(100), nullable=False)
    duration = Column(String(100), nullable=False)
    frequency = Column(String(30), nullable=True)  # OD, BD, TDS, QID, SOS, STAT, HS
    food_relation = Column(String(50), nullable=True)  # Before food, After food, Empty stomach
    timing = Column(JSON, nullable=True)  # ['morning', 'afternoon', 'evening']
    order_index = Column(Integer, default=0, nullable=False)

    prescription = relationship("Prescription", back_populates="medicines")

class CustomMedicine(Base):
    __tablename__ = "custom_medicines"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(200), unique=True, index=True, nullable=False)
    dose = Column(String(100), nullable=True)
    duration = Column(String(100), nullable=True)
    added_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    added_by_email = Column(String(120), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

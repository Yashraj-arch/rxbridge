import re
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.db.models.patient import Patient

def normalize_mobile(raw_mobile: str) -> str:
    digits = re.sub(r"\D", "", raw_mobile)
    if len(digits) >= 10:
        return digits[-10:]
    return digits

def get_patient_by_mobile(db: Session, mobile: str) -> Optional[Patient]:
    clean_mobile = normalize_mobile(mobile)
    return db.query(Patient).filter(Patient.mobile == clean_mobile).first()

def get_or_create_patient(
    db: Session,
    mobile: str,
    name: str,
    age_gender: str,
    weight: Optional[float] = None,
    height: Optional[float] = None,
    consent_offers: bool = False,
    consent_refill: bool = False
) -> Patient:
    clean_mobile = normalize_mobile(mobile)
    patient = db.query(Patient).filter(Patient.mobile == clean_mobile).first()
    if not patient:
        patient = Patient(
            mobile=clean_mobile,
            name=name.strip(),
            age_gender=age_gender.strip(),
            weight=weight,
            height=height,
            consent_offers=consent_offers,
            consent_refill=consent_refill,
            last_consent_at=datetime.now(timezone.utc)
        )
        db.add(patient)
    else:
        # Update demographics with latest known info
        patient.name = name.strip() or patient.name
        patient.age_gender = age_gender.strip() or patient.age_gender
        if weight is not None:
            patient.weight = weight
        if height is not None:
            patient.height = height
        patient.consent_offers = consent_offers
        patient.consent_refill = consent_refill
        patient.last_consent_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(patient)
    return patient

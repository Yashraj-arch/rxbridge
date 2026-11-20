import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, func

from app.db.models.prescription import Prescription
from app.db.models.medicine import PrescriptionMedicine, CustomMedicine
from app.db.models.user import User
from app.schemas.prescription import IntakeCreate, PrescriptionComplete, DirectPrescriptionCreate
from app.crud.crud_patient import normalize_mobile, get_or_create_patient
from app.enums import PrescriptionStatus

def generate_rx_number(db: Session) -> str:
    today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    prefix = f"RX-{today_str}-"
    # Find count of prescriptions created today
    count = db.query(func.count(Prescription.id)).filter(Prescription.rx_number.like(f"{prefix}%")).scalar() or 0
    return f"{prefix}{count + 1:04d}"

def create_intake(db: Session, intake_in: IntakeCreate, staff_user: Optional[User] = None) -> Prescription:
    clean_mobile = normalize_mobile(intake_in.patient_mobile)
    
    # Update or create patient record
    patient = get_or_create_patient(
        db=db,
        mobile=clean_mobile,
        name=intake_in.patient_name,
        age_gender=intake_in.patient_age_gender,
        weight=intake_in.patient_weight,
        height=intake_in.height,
        consent_offers=intake_in.consent_offers,
        consent_refill=intake_in.consent_refill,
    )

    rx_num = generate_rx_number(db)
    prescription = Prescription(
        rx_number=rx_num,
        patient_id=patient.id,
        patient_name=intake_in.patient_name.strip(),
        patient_mobile=clean_mobile,
        patient_age_gender=intake_in.patient_age_gender.strip(),
        patient_weight=intake_in.patient_weight,
        diagnosis=intake_in.diagnosis,
        bp_sys=intake_in.bp_sys,
        bp_dia=intake_in.bp_dia,
        pulse=intake_in.pulse,
        temperature=intake_in.temperature,
        spo2=intake_in.spo2,
        respiratory_rate=intake_in.respiratory_rate,
        height=intake_in.height,
        bmi=intake_in.bmi,
        blood_sugar=intake_in.blood_sugar,
        sugar_type=intake_in.sugar_type,
        status=PrescriptionStatus.INTAKE.value,
        consent_offers=intake_in.consent_offers,
        consent_refill=intake_in.consent_refill,
        consent_recorded_by=staff_user.email if staff_user else None,
        consent_recorded_at=datetime.now(timezone.utc) if (intake_in.consent_offers or intake_in.consent_refill) else None,
        created_by_id=staff_user.id if staff_user else None,
        created_by_email=staff_user.email if staff_user else None,
    )
    db.add(prescription)
    db.commit()
    db.refresh(prescription)
    return prescription

def get_waiting_queue(db: Session) -> List[Prescription]:
    return db.query(Prescription).filter(
        Prescription.status == PrescriptionStatus.INTAKE.value
    ).order_by(Prescription.created_at.asc()).all()

def complete_prescription(
    db: Session,
    prescription_id: int,
    data: PrescriptionComplete,
    doctor: User
) -> Optional[Prescription]:
    rx = db.query(Prescription).filter(Prescription.id == prescription_id).first()
    if not rx:
        return None

    rx.diagnosis = data.diagnosis.strip()
    rx.advice = data.advice.strip() if data.advice else ""
    rx.follow_up_date = data.follow_up_date.strip() if data.follow_up_date else ""
    rx.status = PrescriptionStatus.COMPLETED.value
    rx.doctor_id = doctor.id
    rx.doctor_email = doctor.email
    rx.completed_at = datetime.now(timezone.utc)

    # Snapshot doctor letterhead details (frozen at issue time, BRD FR-4.8)
    rx.doctor_info = {
        "doctorName": doctor.doctor_name or "Doctor",
        "regNo": doctor.reg_no or "",
        "qualification": doctor.qualification or "",
        "clinicName": doctor.clinic_name or "Pharma Bridge Clinic",
        "clinicAddress": doctor.clinic_address or "",
        "clinicPhone": doctor.clinic_phone or "",
        "signatureData": doctor.signature_data or "",
    }

    # Remove existing medicines if updating
    db.query(PrescriptionMedicine).filter(PrescriptionMedicine.prescription_id == rx.id).delete()

    # Add medicines
    for idx, m in enumerate(data.medicines):
        med = PrescriptionMedicine(
            prescription_id=rx.id,
            name=m.name.strip(),
            dose=m.dose.strip(),
            duration=m.duration.strip(),
            frequency=m.frequency or "",
            food_relation=m.food_relation or "",
            timing=m.timing or [],
            order_index=idx
        )
        db.add(med)

        # Self-learning medicine master (BRD FR-4.5)
        existing_custom = db.query(CustomMedicine).filter(CustomMedicine.name == m.name.strip()).first()
        if not existing_custom:
            custom_med = CustomMedicine(
                name=m.name.strip(),
                dose=m.dose.strip(),
                duration=m.duration.strip(),
                added_by_id=doctor.id,
                added_by_email=doctor.email
            )
            db.add(custom_med)

    db.commit()
    db.refresh(rx)
    return rx

def create_direct_prescription(
    db: Session,
    data: DirectPrescriptionCreate,
    doctor: User
) -> Prescription:
    clean_mobile = normalize_mobile(data.patient_mobile)
    patient = get_or_create_patient(
        db=db,
        mobile=clean_mobile,
        name=data.patient_name,
        age_gender=data.patient_age_gender,
        weight=data.patient_weight,
        height=data.height,
        consent_offers=data.consent_offers,
        consent_refill=data.consent_refill
    )

    rx_num = generate_rx_number(db)
    rx = Prescription(
        rx_number=rx_num,
        patient_id=patient.id,
        patient_name=data.patient_name.strip(),
        patient_mobile=clean_mobile,
        patient_age_gender=data.patient_age_gender.strip(),
        patient_weight=data.patient_weight,
        diagnosis=data.diagnosis.strip(),
        bp_sys=data.bp_sys,
        bp_dia=data.bp_dia,
        pulse=data.pulse,
        temperature=data.temperature,
        spo2=data.spo2,
        respiratory_rate=data.respiratory_rate,
        height=data.height,
        bmi=data.bmi,
        blood_sugar=data.blood_sugar,
        sugar_type=data.sugar_type,
        advice=data.advice.strip() if data.advice else "",
        follow_up_date=data.follow_up_date.strip() if data.follow_up_date else "",
        status=PrescriptionStatus.COMPLETED.value,
        consent_offers=data.consent_offers,
        consent_refill=data.consent_refill,
        consent_recorded_by=doctor.email,
        consent_recorded_at=datetime.now(timezone.utc) if (data.consent_offers or data.consent_refill) else None,
        created_by_id=doctor.id,
        created_by_email=doctor.email,
        doctor_id=doctor.id,
        doctor_email=doctor.email,
        completed_at=datetime.now(timezone.utc),
        doctor_info={
            "doctorName": doctor.doctor_name or "Doctor",
            "regNo": doctor.reg_no or "",
            "qualification": doctor.qualification or "",
            "clinicName": doctor.clinic_name or "Pharma Bridge Clinic",
            "clinicAddress": doctor.clinic_address or "",
            "clinicPhone": doctor.clinic_phone or "",
            "signatureData": doctor.signature_data or "",
        }
    )
    db.add(rx)
    db.flush()

    for idx, m in enumerate(data.medicines):
        med = PrescriptionMedicine(
            prescription_id=rx.id,
            name=m.name.strip(),
            dose=m.dose.strip(),
            duration=m.duration.strip(),
            frequency=m.frequency or "",
            food_relation=m.food_relation or "",
            timing=m.timing or [],
            order_index=idx
        )
        db.add(med)

        existing_custom = db.query(CustomMedicine).filter(CustomMedicine.name == m.name.strip()).first()
        if not existing_custom:
            custom_med = CustomMedicine(
                name=m.name.strip(),
                dose=m.dose.strip(),
                duration=m.duration.strip(),
                added_by_id=doctor.id,
                added_by_email=doctor.email
            )
            db.add(custom_med)

    db.commit()
    db.refresh(rx)
    return rx

def get_prescription_by_id(db: Session, prescription_id: int) -> Optional[Prescription]:
    return db.query(Prescription).filter(Prescription.id == prescription_id).first()

def get_prescription_by_rx_number(db: Session, rx_number: str) -> Optional[Prescription]:
    return db.query(Prescription).filter(Prescription.rx_number == rx_number.strip()).first()

def get_history(
    db: Session,
    doctor_id: Optional[int] = None,
    search: Optional[str] = None,
    limit: int = 100
) -> List[Prescription]:
    query = db.query(Prescription).filter(
        Prescription.status.in_([PrescriptionStatus.COMPLETED.value, PrescriptionStatus.DISPENSED.value])
    )
    if doctor_id:
        query = query.filter(Prescription.doctor_id == doctor_id)
    if search:
        s = f"%{search.strip()}%"
        query = query.filter(or_(Prescription.patient_name.ilike(s), Prescription.patient_mobile.ilike(s), Prescription.rx_number.ilike(s)))
    return query.order_by(desc(Prescription.completed_at)).limit(limit).all()

def get_pharmacy_prescriptions(db: Session, search: Optional[str] = None) -> List[Prescription]:
    # Strictly consented prescriptions (BRD FR-9.1, 9.2)
    query = db.query(Prescription).filter(
        Prescription.consent_offers == True,
        Prescription.status.in_([PrescriptionStatus.COMPLETED.value, PrescriptionStatus.DISPENSED.value])
    )
    if search:
        s = f"%{search.strip()}%"
        query = query.filter(or_(Prescription.patient_name.ilike(s), Prescription.patient_mobile.ilike(s)))
    return query.order_by(desc(Prescription.completed_at)).limit(100).all()

def dispense_prescription(db: Session, prescription_id: int, pharmacy_user: User) -> Optional[Prescription]:
    rx = db.query(Prescription).filter(
        Prescription.id == prescription_id,
        Prescription.consent_offers == True
    ).first()
    if not rx:
        return None
    rx.status = PrescriptionStatus.DISPENSED.value
    rx.dispensed_at = datetime.now(timezone.utc)
    rx.dispensed_by_id = pharmacy_user.id
    db.commit()
    db.refresh(rx)
    return rx

def delete_prescription(db: Session, prescription_id: int, doctor_id: int) -> bool:
    rx = db.query(Prescription).filter(
        Prescription.id == prescription_id,
        Prescription.doctor_id == doctor_id
    ).first()
    if not rx:
        return False
    db.delete(rx)
    db.commit()
    return True

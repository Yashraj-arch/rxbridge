from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models.prescription import Prescription
from app.enums import PrescriptionStatus

router = APIRouter(prefix="/verify", tags=["Verification"])

@router.get("/{identifier}")
def verify_prescription(identifier: str, db: Session = Depends(get_db)):
    clean_id = identifier.strip()
    
    # Try searching by rx_number first, then by integer ID
    rx = db.query(Prescription).filter(Prescription.rx_number == clean_id).first()
    if not rx and clean_id.isdigit():
        rx = db.query(Prescription).filter(Prescription.id == int(clean_id)).first()

    if not rx or rx.status == PrescriptionStatus.INTAKE.value:
        return {
            "valid": False,
            "message": "Prescription record not found or not yet finalized by a registered doctor."
        }

    doc_info = rx.doctor_info or {}
    return {
        "valid": True,
        "rxNumber": rx.rx_number,
        "date": rx.completed_at.strftime("%d %b %Y, %I:%M %p") if rx.completed_at else (rx.created_at.strftime("%d %b %Y") if rx.created_at else ""),
        "patientName": rx.patient_name,
        "patientAgeGender": rx.patient_age_gender,
        "doctorName": doc_info.get("doctorName") or "Registered Physician",
        "qualification": doc_info.get("qualification") or "",
        "regNo": doc_info.get("regNo") or "",
        "clinicName": doc_info.get("clinicName") or "Medical Clinic",
        "medicinesCount": len(rx.medicines),
        "status": rx.status,
    }

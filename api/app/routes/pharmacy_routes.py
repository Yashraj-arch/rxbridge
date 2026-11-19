from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies import require_pharmacy, get_current_user
from app.db.models.user import User
from app.schemas.prescription import PrescriptionResponse, PrescriptionSummary
from app.crud.crud_prescription import get_pharmacy_prescriptions, dispense_prescription, get_prescription_by_id
from app.crud.crud_audit import log_audit

router = APIRouter(prefix="/pharmacy", tags=["Pharmacy"])

@router.get("/prescriptions", response_model=List[PrescriptionSummary])
def list_pharmacy_prescriptions(
    search: Optional[str] = Query(None),
    current_user: User = Depends(require_pharmacy),
    db: Session = Depends(get_db)
):
    prescriptions = get_pharmacy_prescriptions(db, search=search)
    return [
        PrescriptionSummary(
            id=p.id,
            rx_number=p.rx_number,
            patient_name=p.patient_name,
            patient_mobile=p.patient_mobile,
            patient_age_gender=p.patient_age_gender,
            diagnosis=p.diagnosis,
            status=p.status,
            consent_offers=p.consent_offers,
            created_at=p.created_at,
            completed_at=p.completed_at,
            medicines_count=len(p.medicines),
            created_by_email=p.created_by_email,
            doctor_email=p.doctor_email,
        )
        for p in prescriptions
    ]

@router.get("/prescriptions/{prescription_id}", response_model=PrescriptionResponse)
def get_pharmacy_prescription_detail(
    prescription_id: int,
    current_user: User = Depends(require_pharmacy),
    db: Session = Depends(get_db)
):
    rx = get_prescription_by_id(db, prescription_id)
    if not rx:
        raise HTTPException(status_code=404, detail="Prescription not found")
    if not rx.consent_offers:
        raise HTTPException(status_code=403, detail="Access denied: patient did not consent to pharmacy offers")
    return rx

@router.post("/prescriptions/{prescription_id}/dispense", response_model=PrescriptionResponse)
def mark_dispensed(
    prescription_id: int,
    current_user: User = Depends(require_pharmacy),
    db: Session = Depends(get_db)
):
    rx = dispense_prescription(db, prescription_id, pharmacy_user=current_user)
    if not rx:
        raise HTTPException(status_code=404, detail="Prescription not found or not eligible for pharmacy dispensing")
    log_audit(db, action="RX_DISPENSED", details=f"Prescription {rx.rx_number} dispensed by {current_user.email}", user_id=current_user.id, user_email=current_user.email)
    return rx

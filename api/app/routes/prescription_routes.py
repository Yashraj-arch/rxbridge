from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies import get_current_user, require_doctor, require_staff_or_doctor
from app.db.models.user import User
from app.enums import UserRole
from app.schemas.prescription import (
    IntakeCreate,
    PrescriptionComplete,
    DirectPrescriptionCreate,
    PrescriptionResponse,
    PrescriptionSummary,
)
from app.crud.crud_prescription import (
    create_intake,
    get_waiting_queue,
    complete_prescription,
    create_direct_prescription,
    get_prescription_by_id,
    get_history,
    delete_prescription,
)
from app.crud.crud_audit import log_audit

router = APIRouter(prefix="/prescriptions", tags=["Prescriptions"])

@router.post("/intake", response_model=PrescriptionResponse, status_code=status.HTTP_201_CREATED)
def record_intake(
    intake_data: IntakeCreate,
    current_user: User = Depends(require_staff_or_doctor),
    db: Session = Depends(get_db)
):
    rx = create_intake(db, intake_data, staff_user=current_user)
    log_audit(db, action="INTAKE_CREATED", details=f"Intake {rx.rx_number} for {rx.patient_name} created by {current_user.email}", user_id=current_user.id, user_email=current_user.email)
    return rx

@router.get("/waiting", response_model=List[PrescriptionResponse])
def waiting_queue(
    current_user: User = Depends(require_doctor),
    db: Session = Depends(get_db)
):
    return get_waiting_queue(db)

@router.post("/{prescription_id}/complete", response_model=PrescriptionResponse)
def complete_rx(
    prescription_id: int,
    data: PrescriptionComplete,
    current_user: User = Depends(require_doctor),
    db: Session = Depends(get_db)
):
    rx = complete_prescription(db, prescription_id, data, doctor=current_user)
    if not rx:
        raise HTTPException(status_code=404, detail="Prescription not found")
    log_audit(db, action="RX_COMPLETED", details=f"Prescription {rx.rx_number} completed by Dr. {current_user.email}", user_id=current_user.id, user_email=current_user.email)
    return rx

@router.post("/direct", response_model=PrescriptionResponse, status_code=status.HTTP_201_CREATED)
def direct_rx(
    data: DirectPrescriptionCreate,
    current_user: User = Depends(require_doctor),
    db: Session = Depends(get_db)
):
    rx = create_direct_prescription(db, data, doctor=current_user)
    log_audit(db, action="RX_DIRECT_CREATED", details=f"Direct Rx {rx.rx_number} created by Dr. {current_user.email}", user_id=current_user.id, user_email=current_user.email)
    return rx

@router.get("/history", response_model=List[PrescriptionSummary])
def history(
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # As per BRD FR-8.1: doctors see their own, staff sees clinic-wide completed
    doc_id = current_user.id if current_user.role == UserRole.DOCTOR.value else None
    prescriptions = get_history(db, doctor_id=doc_id, search=search)
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

@router.get("/{prescription_id}", response_model=PrescriptionResponse)
def get_rx_details(
    prescription_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    rx = get_prescription_by_id(db, prescription_id)
    if not rx:
        raise HTTPException(status_code=404, detail="Prescription not found")
    
    # Restrict pharmacy view to consented prescriptions only (BRD FR-9.2)
    if current_user.role == UserRole.PHARMACY.value and not rx.consent_offers:
        raise HTTPException(status_code=403, detail="Access denied: patient did not consent to pharmacy offers")
        
    return rx

@router.delete("/{prescription_id}")
def delete_rx(
    prescription_id: int,
    current_user: User = Depends(require_doctor),
    db: Session = Depends(get_db)
):
    success = delete_prescription(db, prescription_id, doctor_id=current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Prescription not found or unauthorized to delete")
    log_audit(db, action="RX_DELETED", details=f"Prescription ID {prescription_id} deleted by {current_user.email}", user_id=current_user.id, user_email=current_user.email)
    return {"message": "Prescription deleted successfully"}

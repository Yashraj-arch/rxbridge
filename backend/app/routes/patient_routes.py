from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.db.database import get_db
from app.dependencies import get_current_user
from app.db.models.user import User
from app.db.models.prescription import Prescription
from app.db.models.lab_report import LabReport
from app.crud.crud_patient import normalize_mobile, get_patient_by_mobile
from app.schemas.prescription import PrescriptionResponse
from app.schemas.lab_report import LabReportResponse

router = APIRouter(prefix="/patients", tags=["Patients"])

@router.get("/{mobile}")
def get_patient_profile(
    mobile: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    clean_mobile = normalize_mobile(mobile)
    patient = get_patient_by_mobile(db, clean_mobile)
    
    # Also fetch lab reports for this mobile
    reports = db.query(LabReport).filter(LabReport.patient_mobile == clean_mobile).order_by(desc(LabReport.uploaded_at)).all()
    reports_data = [
        {
            "id": r.id,
            "fileName": r.file_name,
            "url": r.file_url,
            "publicId": r.public_id,
            "uploadedAt": r.uploaded_at.isoformat() if r.uploaded_at else None,
            "uploadedBy": r.uploaded_by_email,
        }
        for r in reports
    ]

    if not patient:
        return {
            "found": False,
            "mobile": clean_mobile,
            "reports": reports_data
        }

    return {
        "found": True,
        "mobile": patient.mobile,
        "name": patient.name,
        "ageGender": patient.age_gender,
        "weight": patient.weight,
        "height": patient.height,
        "consentOffers": patient.consent_offers,
        "consentRefill": patient.consent_refill,
        "lastConsentAt": patient.last_consent_at.isoformat() if patient.last_consent_at else None,
        "reports": reports_data
    }

@router.get("/{mobile}/timeline")
def get_patient_timeline(
    mobile: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    clean_mobile = normalize_mobile(mobile)
    prescriptions = db.query(Prescription).filter(
        Prescription.patient_mobile == clean_mobile,
        Prescription.status.in_(["completed", "dispensed"])
    ).order_by(desc(Prescription.completed_at)).all()

    reports = db.query(LabReport).filter(LabReport.patient_mobile == clean_mobile).order_by(desc(LabReport.uploaded_at)).all()

    return {
        "mobile": clean_mobile,
        "visits": [
            {
                "id": p.id,
                "rxNumber": p.rx_number,
                "date": p.completed_at.strftime("%d %b %Y") if p.completed_at else (p.created_at.strftime("%d %b %Y") if p.created_at else ""),
                "diagnosis": p.diagnosis,
                "doctorName": p.doctor_info.get("doctorName") if p.doctor_info else "Doctor",
                "advice": p.advice,
                "vitals": {
                    "bp": f"{p.bp_sys}/{p.bp_dia}" if (p.bp_sys and p.bp_dia) else "—",
                    "pulse": p.pulse,
                    "temp": p.temperature,
                    "spo2": p.spo2,
                    "bmi": p.bmi,
                },
                "medicines": [
                    {
                        "name": m.name,
                        "dose": m.dose,
                        "duration": m.duration,
                        "frequency": m.frequency,
                        "foodRelation": m.food_relation,
                    }
                    for m in p.medicines
                ]
            }
            for p in prescriptions
        ],
        "reports": [
            {
                "id": r.id,
                "fileName": r.file_name,
                "url": r.file_url,
                "uploadedAt": r.uploaded_at.isoformat() if r.uploaded_at else "",
            }
            for r in reports
        ]
    }

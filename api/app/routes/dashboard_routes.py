from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.db.database import get_db
from app.dependencies import require_doctor
from app.db.models.user import User
from app.db.models.prescription import Prescription
from app.db.models.medicine import PrescriptionMedicine
from app.db.models.patient import Patient
from app.enums import PrescriptionStatus

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/stats")
def get_dashboard_stats(
    current_user: User = Depends(require_doctor),
    db: Session = Depends(get_db)
):
    now = datetime.now(timezone.utc)
    today_start = datetime(now.year, now.month, now.day, 0, 0, 0, tzinfo=timezone.utc)
    month_start = datetime(now.year, now.month, 1, 0, 0, 0, tzinfo=timezone.utc)

    # Base query for completed/dispensed
    completed_filter = Prescription.status.in_([PrescriptionStatus.COMPLETED.value, PrescriptionStatus.DISPENSED.value])

    # Prescriptions today
    count_today = db.query(func.count(Prescription.id)).filter(
        completed_filter,
        Prescription.completed_at >= today_start
    ).scalar() or 0

    # Prescriptions this month
    count_month = db.query(func.count(Prescription.id)).filter(
        completed_filter,
        Prescription.completed_at >= month_start
    ).scalar() or 0

    # Distinct patients
    distinct_patients = db.query(func.count(func.distinct(Prescription.patient_mobile))).filter(
        completed_filter
    ).scalar() or 0

    # Top 5 medicines
    top_meds_query = db.query(
        PrescriptionMedicine.name,
        func.count(PrescriptionMedicine.id).label("total")
    ).join(Prescription, Prescription.id == PrescriptionMedicine.prescription_id).filter(
        completed_filter
    ).group_by(PrescriptionMedicine.name).order_by(desc("total")).limit(5).all()

    top_medicines = [{"name": r[0], "count": r[1]} for r in top_meds_query]

    return {
        "today": count_today,
        "thisMonth": count_month,
        "distinctPatients": distinct_patients,
        "topMedicines": top_medicines
    }

from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, func

from app.db.database import get_db
from app.dependencies import require_pharmacy, get_current_user
from app.db.models.user import User
from app.db.models.prescription import Prescription
from app.db.models.medicine import PrescriptionMedicine
from app.crud.crud_audit import log_audit
from app.enums import PrescriptionStatus

router = APIRouter(prefix="/distributor", tags=["Central Distributor Hub"])

class OrderStatusUpdate(BaseModel):
    status: str  # pending, packing, out_for_delivery, delivered
    notes: Optional[str] = None
    estimated_value: Optional[float] = None

@router.get("/stats")
def get_distributor_stats(
    current_user: User = Depends(require_pharmacy),
    db: Session = Depends(get_db)
):
    """
    Returns high-level fulfillment KPIs, chronic refill counts, and doctor commissions.
    """
    base_query = db.query(Prescription).filter(
        Prescription.consent_offers == True,
        Prescription.status.in_([PrescriptionStatus.COMPLETED.value, PrescriptionStatus.DISPENSED.value])
    )
    
    total_orders = base_query.count()
    pending = base_query.filter(Prescription.fulfillment_status == "pending").count()
    packing = base_query.filter(Prescription.fulfillment_status == "packing").count()
    out_for_delivery = base_query.filter(Prescription.fulfillment_status == "out_for_delivery").count()
    delivered = base_query.filter(Prescription.fulfillment_status == "delivered").count()
    
    # Calculate estimated GMV and commissions
    all_consented = base_query.all()
    total_gmv = 0.0
    total_commission = 0.0
    
    for rx in all_consented:
        # Default estimation: ₹350 per unique medicine prescribed if value not explicitly keyed
        rx_val = rx.estimated_value or (len(rx.medicines) * 350.0)
        comm_rate = (rx.commission_rate or 15.0) / 100.0
        total_gmv += rx_val
        total_commission += (rx_val * comm_rate)

    # Estimate chronic refills due in next 7 days
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    refills_due_count = db.query(Prescription).filter(
        Prescription.consent_refill == True,
        Prescription.completed_at <= datetime.now(timezone.utc) - timedelta(days=23),
        Prescription.completed_at >= datetime.now(timezone.utc) - timedelta(days=35)
    ).count()

    return {
        "total_orders": total_orders,
        "pending": pending,
        "packing": packing,
        "out_for_delivery": out_for_delivery,
        "delivered": delivered,
        "refills_due_next_7_days": refills_due_count,
        "total_gmv": round(total_gmv, 2),
        "total_doctor_commission": round(total_commission, 2)
    }

@router.get("/orders")
def list_distributor_orders(
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    limit: int = 100,
    current_user: User = Depends(require_pharmacy),
    db: Session = Depends(get_db)
):
    """
    Stream of hospital prescriptions with explicit patient consent for home delivery fulfillment.
    """
    query = db.query(Prescription).filter(
        Prescription.consent_offers == True,
        Prescription.status.in_([PrescriptionStatus.COMPLETED.value, PrescriptionStatus.DISPENSED.value])
    )
    
    if status_filter and status_filter.lower() != "all":
        query = query.filter(Prescription.fulfillment_status == status_filter.lower())
        
    if search:
        s = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Prescription.patient_name.ilike(s),
                Prescription.patient_mobile.ilike(s),
                Prescription.rx_number.ilike(s),
                Prescription.doctor_email.ilike(s)
            )
        )
        
    prescriptions = query.order_by(desc(Prescription.completed_at)).limit(limit).all()
    
    results = []
    for rx in prescriptions:
        doc_info = rx.doctor_info or {}
        meds = [
            {
                "id": m.id,
                "name": m.name,
                "dose": m.dose,
                "frequency": m.frequency,
                "food_relation": m.food_relation,
                "duration": m.duration,
                "is_chronic": any(term in (m.duration or "").lower() for term in ["30", "month", "continue", "daily", "regular"])
            }
            for m in rx.medicines
        ]
        
        est_val = rx.estimated_value or (len(meds) * 350.0)
        comm_pct = rx.commission_rate or 15.0
        doc_comm = est_val * (comm_pct / 100.0)
        
        results.append({
            "id": rx.id,
            "rx_number": rx.rx_number,
            "patient_name": rx.patient_name,
            "patient_mobile": rx.patient_mobile,
            "patient_age_gender": rx.patient_age_gender,
            "diagnosis": rx.diagnosis,
            "doctor_name": doc_info.get("doctorName") or (rx.doctor_email or "Consulting Physician"),
            "clinic_name": doc_info.get("clinicName") or "Partner Clinic",
            "clinic_phone": doc_info.get("clinicPhone") or "",
            "completed_at": rx.completed_at.isoformat() if rx.completed_at else None,
            "pdf_url": rx.pdf_url,
            "fulfillment_status": rx.fulfillment_status or "pending",
            "dispatch_notes": rx.dispatch_notes,
            "dispatched_at": rx.dispatched_at.isoformat() if rx.dispatched_at else None,
            "estimated_value": round(est_val, 2),
            "commission_rate": comm_pct,
            "doctor_commission": round(doc_comm, 2),
            "medicines": meds,
            "medicines_count": len(meds)
        })
        
    return results

@router.post("/orders/{rx_id}/status")
def update_fulfillment_status(
    rx_id: int,
    payload: OrderStatusUpdate,
    current_user: User = Depends(require_pharmacy),
    db: Session = Depends(get_db)
):
    """
    Updates the physical fulfillment and delivery status of a prescription order.
    """
    valid_statuses = ["pending", "packing", "out_for_delivery", "delivered"]
    clean_status = payload.status.lower().strip()
    if clean_status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{payload.status}'. Must be one of: {valid_statuses}"
        )
        
    rx = db.query(Prescription).filter(Prescription.id == rx_id).first()
    if not rx:
        raise HTTPException(status_code=404, detail=f"Prescription {rx_id} not found")
        
    rx.fulfillment_status = clean_status
    if payload.notes is not None:
        rx.dispatch_notes = payload.notes.strip()
    if payload.estimated_value is not None:
        rx.estimated_value = payload.estimated_value
        
    if clean_status == "out_for_delivery":
        rx.dispatched_at = datetime.now(timezone.utc)
    elif clean_status == "delivered":
        rx.status = PrescriptionStatus.DISPENSED.value
        rx.dispensed_at = datetime.now(timezone.utc)
        rx.dispensed_by_id = current_user.id
        
    db.commit()
    db.refresh(rx)
    
    log_audit(
        db,
        action="DISTRIBUTOR_STATUS_UPDATE",
        details=f"Order {rx.rx_number} transitioned to '{clean_status}' by distributor {current_user.email}",
        user_id=current_user.id,
        user_email=current_user.email
    )
    
    return {
        "id": rx.id,
        "rx_number": rx.rx_number,
        "fulfillment_status": rx.fulfillment_status,
        "dispatch_notes": rx.dispatch_notes,
        "dispatched_at": rx.dispatched_at.isoformat() if rx.dispatched_at else None,
        "estimated_value": rx.estimated_value
    }

@router.get("/refills")
def get_chronic_refill_candidates(
    current_user: User = Depends(require_pharmacy),
    db: Session = Depends(get_db)
):
    """
    Detects patients on chronic medications approaching their 30-day supply exhaustion.
    Powers automated recurring medicine delivery and WhatsApp refill reminders.
    """
    now = datetime.now(timezone.utc)
    # Search prescriptions created between 20 and 45 days ago
    start_window = now - timedelta(days=45)
    
    prescriptions = db.query(Prescription).filter(
        Prescription.consent_refill == True,
        Prescription.completed_at >= start_window,
        Prescription.status.in_([PrescriptionStatus.COMPLETED.value, PrescriptionStatus.DISPENSED.value])
    ).order_by(desc(Prescription.completed_at)).all()
    
    refill_list = []
    for rx in prescriptions:
        # Check for chronic indicators
        has_chronic = False
        chronic_meds = []
        for m in rx.medicines:
            dur = (m.duration or "").lower()
            if any(t in dur for t in ["30", "month", "continue", "daily", "regular"]) or len(rx.medicines) >= 2:
                has_chronic = True
                chronic_meds.append(f"{m.name} ({m.dose or ''})")
                
        if has_chronic and rx.completed_at:
            # Assume 30-day standard cycle
            target_date = rx.completed_at + timedelta(days=30)
            days_remaining = (target_date - now).days
            
            doc_info = rx.doctor_info or {}
            refill_list.append({
                "rx_id": rx.id,
                "rx_number": rx.rx_number,
                "patient_name": rx.patient_name,
                "patient_mobile": rx.patient_mobile,
                "doctor_name": doc_info.get("doctorName") or "Consulting Physician",
                "clinic_name": doc_info.get("clinicName") or "Partner Clinic",
                "issued_date": rx.completed_at.strftime("%d %b %Y"),
                "estimated_refill_date": target_date.strftime("%d %b %Y"),
                "days_until_refill": days_remaining,
                "urgency": "Urgent (Due Now)" if days_remaining <= 3 else ("Upcoming (Next 7 Days)" if days_remaining <= 7 else "Active Cycle"),
                "chronic_medicines": chronic_meds,
                "pdf_url": rx.pdf_url
            })
            
    # Sort by nearest refill due date
    refill_list.sort(key=lambda x: x["days_until_refill"])
    return refill_list

@router.get("/commissions")
def get_doctor_commission_ledger(
    current_user: User = Depends(require_pharmacy),
    db: Session = Depends(get_db)
):
    """
    Summarizes orders and calculates 10%–20% partner commissions per doctor/clinic.
    """
    prescriptions = db.query(Prescription).filter(
        Prescription.consent_offers == True,
        Prescription.status.in_([PrescriptionStatus.COMPLETED.value, PrescriptionStatus.DISPENSED.value])
    ).all()
    
    ledger: Dict[str, Dict[str, Any]] = {}
    
    for rx in prescriptions:
        key = rx.doctor_email or "unknown_doctor"
        doc_info = rx.doctor_info or {}
        doctor_name = doc_info.get("doctorName") or (rx.doctor_email or "Doctor")
        clinic_name = doc_info.get("clinicName") or "Partner Clinic"
        
        if key not in ledger:
            ledger[key] = {
                "doctor_email": key,
                "doctor_name": doctor_name,
                "clinic_name": clinic_name,
                "orders_count": 0,
                "medicines_dispensed": 0,
                "total_order_value": 0.0,
                "commission_rate": rx.commission_rate or 15.0,
                "commission_payable": 0.0
            }
            
        est_val = rx.estimated_value or (len(rx.medicines) * 350.0)
        comm_pct = (rx.commission_rate or 15.0) / 100.0
        
        ledger[key]["orders_count"] += 1
        ledger[key]["medicines_dispensed"] += len(rx.medicines)
        ledger[key]["total_order_value"] += est_val
        ledger[key]["commission_payable"] += (est_val * comm_pct)
        
    return [
        {
            "doctor_email": v["doctor_email"],
            "doctor_name": v["doctor_name"],
            "clinic_name": v["clinic_name"],
            "orders_count": v["orders_count"],
            "medicines_dispensed": v["medicines_dispensed"],
            "total_order_value": round(v["total_order_value"], 2),
            "commission_rate": v["commission_rate"],
            "commission_payable": round(v["commission_payable"], 2)
        }
        for v in ledger.values()
    ]

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies import get_current_user
from app.db.models.user import User
from app.db.models.medicine import CustomMedicine
from app.crud.crud_medicine import search_medicines, get_all_medicines
from app.schemas.medicine import CustomMedicineCreate, CustomMedicineResponse

router = APIRouter(prefix="/medicines", tags=["Medicines"])

@router.get("/autocomplete")
def autocomplete(
    q: str = Query("", min_length=1),
    limit: int = Query(8, ge=1, le=20),
    db: Session = Depends(get_db)
):
    results = search_medicines(db, query=q, limit=limit)
    return results

@router.get("/all")
def all_medicines(db: Session = Depends(get_db)):
    return get_all_medicines(db)

@router.post("/custom", response_model=CustomMedicineResponse, status_code=status.HTTP_201_CREATED)
def add_custom(
    med_in: CustomMedicineCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    name = med_in.name.strip()
    existing = db.query(CustomMedicine).filter(CustomMedicine.name == name).first()
    if existing:
        return existing
    
    cm = CustomMedicine(
        name=name,
        dose=med_in.dose,
        duration=med_in.duration,
        added_by_id=current_user.id,
        added_by_email=current_user.email
    )
    db.add(cm)
    db.commit()
    db.refresh(cm)
    return cm

import re
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime
from app.schemas.medicine import MedicineItemSchema

def sanitize_text(text: Optional[str], max_len: int = 500) -> Optional[str]:
    if text is None:
        return None
    cleaned = text.strip()
    # Strip potential HTML tags / scripts for XSS prevention
    cleaned = re.sub(r"<[^>]*>", "", cleaned)
    return cleaned[:max_len]

class IntakeCreate(BaseModel):
    patient_name: str = Field(..., min_length=2, max_length=120)
    patient_age_gender: str = Field(..., min_length=2, max_length=50)
    patient_mobile: str = Field(..., min_length=10, max_length=15)
    patient_weight: Optional[float] = Field(None, ge=1.0, le=350.0)
    diagnosis: Optional[str] = Field("", max_length=500)
    
    # Vitals Plausibility Ranges (BRD FR-2.4)
    bp_sys: Optional[int] = Field(None, ge=60, le=260)
    bp_dia: Optional[int] = Field(None, ge=40, le=160)
    pulse: Optional[int] = Field(None, ge=30, le=220)
    temperature: Optional[float] = Field(None, ge=90.0, le=110.0)
    spo2: Optional[int] = Field(None, ge=50, le=100)
    respiratory_rate: Optional[int] = Field(None, ge=5, le=60)
    height: Optional[float] = Field(None, ge=30.0, le=250.0)
    bmi: Optional[float] = Field(None, ge=5.0, le=90.0)
    blood_sugar: Optional[int] = Field(None, ge=20, le=600)
    sugar_type: Optional[str] = Field("Random", max_length=30)

    # Consent
    consent_offers: bool = False
    consent_refill: bool = False

    @field_validator("patient_name")
    def validate_name(cls, v: str) -> str:
        cleaned = sanitize_text(v, 120)
        if not cleaned or len(cleaned) < 2:
            raise ValueError("Patient name must be at least 2 characters long")
        return cleaned

    @field_validator("patient_mobile")
    def validate_mobile(cls, v: str) -> str:
        digits = re.sub(r"\D", "", v)
        if len(digits) >= 10:
            digits = digits[-10:]
        if not re.match(r"^[6-9]\d{9}$", digits):
            raise ValueError("Patient mobile number must be a valid 10-digit Indian phone number starting with 6, 7, 8, or 9")
        return digits

    @model_validator(mode="after")
    def validate_blood_pressure(self):
        if self.bp_sys is not None and self.bp_dia is not None:
            if self.bp_sys <= self.bp_dia:
                raise ValueError("Systolic blood pressure must be strictly greater than diastolic blood pressure")
        return self

class PrescriptionComplete(BaseModel):
    diagnosis: str = Field(..., min_length=2, max_length=500)
    medicines: List[MedicineItemSchema] = Field(..., min_items=1)
    advice: Optional[str] = Field("", max_length=1500)
    follow_up_date: Optional[str] = Field("", max_length=60)

    @field_validator("diagnosis")
    def clean_diagnosis(cls, v: str) -> str:
        cleaned = sanitize_text(v, 500)
        if not cleaned or len(cleaned) < 2:
            raise ValueError("Diagnosis must be at least 2 characters long")
        return cleaned

    @field_validator("advice")
    def clean_advice(cls, v: Optional[str]) -> Optional[str]:
        return sanitize_text(v, 1500)

class DirectPrescriptionCreate(IntakeCreate):
    diagnosis: str = Field(..., min_length=2, max_length=500)
    medicines: List[MedicineItemSchema] = Field(..., min_items=1)
    advice: Optional[str] = Field("", max_length=1500)
    follow_up_date: Optional[str] = Field("", max_length=60)

    @field_validator("diagnosis")
    def clean_direct_diagnosis(cls, v: str) -> str:
        cleaned = sanitize_text(v, 500)
        if not cleaned or len(cleaned) < 2:
            raise ValueError("Diagnosis must be at least 2 characters long")
        return cleaned

class PrescriptionResponse(BaseModel):
    id: int
    rx_number: str
    patient_name: str
    patient_mobile: str
    patient_age_gender: str
    patient_weight: Optional[float] = None
    diagnosis: Optional[str] = None
    
    # Vitals
    bp_sys: Optional[int] = None
    bp_dia: Optional[int] = None
    pulse: Optional[int] = None
    temperature: Optional[float] = None
    spo2: Optional[int] = None
    respiratory_rate: Optional[int] = None
    height: Optional[float] = None
    bmi: Optional[float] = None
    blood_sugar: Optional[int] = None
    sugar_type: Optional[str] = None

    # Advice & follow up
    advice: Optional[str] = None
    follow_up_date: Optional[str] = None
    status: str

    # Consent
    consent_offers: bool
    consent_refill: bool
    consent_recorded_by: Optional[str] = None
    consent_recorded_at: Optional[datetime] = None

    # Doctor snapshot
    doctor_info: Optional[Dict[str, Any]] = None
    doctor_email: Optional[str] = None
    created_by_email: Optional[str] = None

    # Medicines
    medicines: List[MedicineItemSchema] = []

    # Dispensed
    dispensed_at: Optional[datetime] = None

    # Dates
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class PrescriptionSummary(BaseModel):
    id: int
    rx_number: str
    patient_name: str
    patient_mobile: str
    patient_age_gender: str
    diagnosis: Optional[str] = None
    status: str
    consent_offers: bool
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    medicines_count: int = 0
    created_by_email: Optional[str] = None
    doctor_email: Optional[str] = None

    class Config:
        from_attributes = True

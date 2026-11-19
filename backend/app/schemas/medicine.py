import re
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
from datetime import datetime

ALLOWED_FREQUENCIES = {"OD", "BD", "TDS", "QID", "SOS", "STAT", "HS", ""}
ALLOWED_FOOD_RELATIONS = {"Before food", "After food", "Empty stomach", ""}

def sanitize_str(text: Optional[str], max_len: int = 150) -> str:
    if not text:
        return ""
    cleaned = re.sub(r"<[^>]*>", "", text.strip())
    return cleaned[:max_len]

class MedicineItemSchema(BaseModel):
    name: str = Field(..., min_length=1, max_length=180)
    dose: str = Field(..., min_length=1, max_length=100)
    duration: str = Field(..., min_length=1, max_length=100)
    frequency: Optional[str] = ""
    food_relation: Optional[str] = ""
    timing: Optional[List[str]] = []

    @field_validator("name")
    def clean_name(cls, v: str) -> str:
        s = sanitize_str(v, 180)
        if not s:
            raise ValueError("Medicine name cannot be empty")
        return s

    @field_validator("dose")
    def clean_dose(cls, v: str) -> str:
        s = sanitize_str(v, 100)
        if not s:
            raise ValueError("Dose cannot be empty")
        return s

    @field_validator("duration")
    def clean_duration(cls, v: str) -> str:
        s = sanitize_str(v, 100)
        if not s:
            raise ValueError("Duration cannot be empty")
        return s

    @field_validator("frequency")
    def validate_freq(cls, v: Optional[str]) -> str:
        val = (v or "").strip()
        if val and val not in ALLOWED_FREQUENCIES:
            raise ValueError(f"Invalid frequency '{val}'. Allowed: {ALLOWED_FREQUENCIES}")
        return val

    @field_validator("food_relation")
    def validate_food(cls, v: Optional[str]) -> str:
        val = (v or "").strip()
        if val and val not in ALLOWED_FOOD_RELATIONS:
            raise ValueError(f"Invalid food relation '{val}'. Allowed: {ALLOWED_FOOD_RELATIONS}")
        return val

    class Config:
        from_attributes = True

class CustomMedicineCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=180)
    dose: Optional[str] = Field(None, max_length=100)
    duration: Optional[str] = Field(None, max_length=100)

    @field_validator("name")
    def clean_custom_name(cls, v: str) -> str:
        s = sanitize_str(v, 180)
        if len(s) < 2:
            raise ValueError("Medicine name must be at least 2 characters long")
        return s

class CustomMedicineResponse(BaseModel):
    id: int
    name: str
    dose: Optional[str] = None
    duration: Optional[str] = None
    added_by_email: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

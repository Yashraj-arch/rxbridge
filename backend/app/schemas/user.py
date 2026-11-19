from typing import Optional
from pydantic import BaseModel, Field, field_validator
from datetime import datetime

try:
    import email_validator
    from pydantic import EmailStr
except ImportError:
    EmailStr = str

class UserBase(BaseModel):
    email: EmailStr
    role: str = "doctor"

    @field_validator("role")
    def validate_role(cls, v: str) -> str:
        clean_role = v.strip().lower()
        if clean_role not in ["doctor", "staff", "pharmacy"]:
            raise ValueError("Role must be one of: 'doctor', 'staff', 'pharmacy'")
        return clean_role

class UserLogin(BaseModel):
    email: str = Field(..., min_length=3, max_length=120)
    password: str = Field(..., min_length=4, max_length=100)

class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=100)
    doctor_name: Optional[str] = Field(None, max_length=150)
    reg_no: Optional[str] = Field(None, max_length=100)
    qualification: Optional[str] = Field(None, max_length=150)
    clinic_name: Optional[str] = Field(None, max_length=200)
    clinic_address: Optional[str] = Field(None, max_length=300)
    clinic_phone: Optional[str] = Field(None, max_length=50)

class DoctorSettingsUpdate(BaseModel):
    doctor_name: Optional[str] = Field(None, max_length=150)
    reg_no: Optional[str] = Field(None, max_length=100)
    qualification: Optional[str] = Field(None, max_length=150)
    clinic_name: Optional[str] = Field(None, max_length=200)
    clinic_address: Optional[str] = Field(None, max_length=300)
    clinic_phone: Optional[str] = Field(None, max_length=50)
    signature_data: Optional[str] = None  # Base64 data URL

class UserResponse(BaseModel):
    id: int
    email: str
    role: str
    is_active: bool
    doctor_name: Optional[str] = None
    reg_no: Optional[str] = None
    qualification: Optional[str] = None
    clinic_name: Optional[str] = None
    clinic_address: Optional[str] = None
    clinic_phone: Optional[str] = None
    signature_data: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

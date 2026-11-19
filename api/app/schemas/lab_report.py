from typing import Optional
from pydantic import BaseModel
from datetime import datetime

class LabReportResponse(BaseModel):
    id: int
    patient_mobile: str
    file_name: str
    file_url: str
    public_id: Optional[str] = None
    uploaded_by_email: Optional[str] = None
    uploaded_at: Optional[datetime] = None

    class Config:
        from_attributes = True

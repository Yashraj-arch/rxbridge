import os
import uuid
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.dependencies import get_current_user
from app.db.models.user import User
from app.db.models.lab_report import LabReport
from app.crud.crud_patient import normalize_mobile, get_or_create_patient
from app.crud.crud_audit import log_audit
from app.core.config import settings

router = APIRouter(prefix="/uploads", tags=["Uploads"])

ALLOWED_MIME_EXTENSIONS = {
    ".jpg": ["image/jpeg", "image/pjpeg"],
    ".jpeg": ["image/jpeg", "image/pjpeg"],
    ".png": ["image/png"],
    ".pdf": ["application/pdf"],
}

def verify_magic_bytes(content: bytes, ext: str) -> bool:
    if ext in [".jpg", ".jpeg"]:
        return content.startswith(b"\xff\xd8\xff")
    if ext == ".png":
        return content.startswith(b"\x89PNG\r\n\x1a\n")
    if ext == ".pdf":
        return content.startswith(b"%PDF-")
    return False

@router.post("/lab-report")
async def upload_lab_report(
    mobile: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    clean_mobile = normalize_mobile(mobile)
    if not clean_mobile or len(clean_mobile) != 10:
        raise HTTPException(status_code=400, detail="Valid 10-digit Indian mobile number is required")

    # Sanitize and validate extension
    original_filename = os.path.basename(file.filename or "upload.jpg")
    ext = os.path.splitext(original_filename)[1].lower()
    
    if ext not in ALLOWED_MIME_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file extension '{ext}'. Only JPG, JPEG, PNG, and PDF files are permitted."
        )

    # Read content and enforce size limit
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10 MB limit as per BRD FR-5.2
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds maximum permitted limit of 10 MB"
        )
    if len(content) < 10:
        raise HTTPException(status_code=400, detail="Uploaded file is empty or corrupted")

    # Magic Bytes Validation (Protection against disguised malicious files)
    if not verify_magic_bytes(content, ext):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File content does not match its declared image/document type"
        )

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    # Generate safe random UUID filename (prevents directory traversal attacks)
    unique_name = f"{clean_mobile}_{uuid.uuid4().hex[:12]}{ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, unique_name)

    with open(file_path, "wb") as f:
        f.write(content)

    file_url = f"/uploads/lab_reports/{unique_name}"

    # Ensure patient exists or create stub
    get_or_create_patient(db=db, mobile=clean_mobile, name="Patient", age_gender="")

    # Persist in DB
    report = LabReport(
        patient_mobile=clean_mobile,
        file_name=original_filename,
        file_url=file_url,
        public_id=unique_name,
        uploaded_by_id=current_user.id,
        uploaded_by_email=current_user.email
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    log_audit(
        db,
        action="LAB_REPORT_UPLOADED",
        details=f"Verified lab report {original_filename} uploaded for patient {clean_mobile}",
        user_id=current_user.id,
        user_email=current_user.email
    )

    return {
        "id": report.id,
        "mobile": clean_mobile,
        "fileName": report.file_name,
        "url": report.file_url,
        "uploadedAt": report.uploaded_at.isoformat()
    }

from typing import Optional
from sqlalchemy.orm import Session
from app.db.models.user import User
from app.core.security import get_password_hash, verify_password
from app.schemas.user import UserCreate, DoctorSettingsUpdate

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email.strip().lower()).first()

def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()

def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

def create_user(db: Session, user_in: UserCreate) -> User:
    user = User(
        email=user_in.email.strip().lower(),
        hashed_password=get_password_hash(user_in.password),
        role=user_in.role.lower(),
        doctor_name=user_in.doctor_name,
        reg_no=user_in.reg_no,
        qualification=user_in.qualification,
        clinic_name=user_in.clinic_name,
        clinic_address=user_in.clinic_address,
        clinic_phone=user_in.clinic_phone,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def update_doctor_settings(db: Session, user: User, settings_in: DoctorSettingsUpdate) -> User:
    if settings_in.doctor_name is not None:
        user.doctor_name = settings_in.doctor_name
    if settings_in.reg_no is not None:
        user.reg_no = settings_in.reg_no
    if settings_in.qualification is not None:
        user.qualification = settings_in.qualification
    if settings_in.clinic_name is not None:
        user.clinic_name = settings_in.clinic_name
    if settings_in.clinic_address is not None:
        user.clinic_address = settings_in.clinic_address
    if settings_in.clinic_phone is not None:
        user.clinic_phone = settings_in.clinic_phone
    if settings_in.signature_data is not None:
        user.signature_data = settings_in.signature_data
    db.commit()
    db.refresh(user)
    return user

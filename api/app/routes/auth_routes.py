from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.core.security import create_access_token
from app.crud.crud_user import authenticate_user, create_user, get_user_by_email, update_doctor_settings
from app.crud.crud_audit import log_audit
from app.schemas.user import UserLogin, UserCreate, UserResponse, DoctorSettingsUpdate, Token
from app.dependencies import get_current_user
from app.db.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=Token)
def login(login_data: UserLogin, request: Request, db: Session = Depends(get_db)):
    user = authenticate_user(db, email=login_data.email, password=login_data.password)
    client_ip = request.client.host if request.client else None
    
    if not user:
        log_audit(db, action="LOGIN_FAILED", details=f"Failed login attempt for {login_data.email}", ip_address=client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )
    
    access_token = create_access_token(data={"sub": str(user.id), "email": user.email, "role": user.role})
    log_audit(db, action="LOGIN_SUCCESS", details=f"User {user.email} logged in with role {user.role}", user_id=user.id, user_email=user.email, ip_address=client_ip)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    existing = get_user_by_email(db, user_in.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    user = create_user(db, user_in)
    return user

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.put("/settings", response_model=UserResponse)
def update_settings(
    settings_in: DoctorSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    updated_user = update_doctor_settings(db, current_user, settings_in)
    log_audit(db, action="SETTINGS_UPDATED", details=f"Doctor settings updated by {current_user.email}", user_id=current_user.id, user_email=current_user.email)
    return updated_user

@router.post("/logout")
def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    client_ip = request.client.host if request.client else None
    log_audit(db, action="LOGOUT", details=f"User {current_user.email} logged out", user_id=current_user.id, user_email=current_user.email, ip_address=client_ip)
    return {"message": "Logged out successfully"}

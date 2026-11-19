import os
import sys

_current = os.path.dirname(os.path.abspath(__file__))
_api_dir = os.path.dirname(_current)
_root_dir = os.path.dirname(_api_dir)
for _p in [_api_dir, _current, _root_dir, "/var/task/api", "/var/task"]:
    if _p and _p not in sys.path:
        sys.path.insert(0, _p)

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.security_middleware import SecurityHeadersMiddleware, RateLimitMiddleware
from app.db.database import engine, SessionLocal
from app.db.base import Base
import app.db.models  # Ensure all models are registered with Base.metadata

from app.routes.auth_routes import router as auth_router
from app.routes.prescription_routes import router as prescription_router
from app.routes.patient_routes import router as patient_router
from app.routes.medicine_routes import router as medicine_router
from app.routes.pharmacy_routes import router as pharmacy_router
from app.routes.upload_routes import router as upload_router
from app.routes.dashboard_routes import router as dashboard_router
from app.routes.verify_routes import router as verify_router
from app.routes.agent_routes import router as agent_router

from app.db.models.user import User
from app.db.models.medicine import CustomMedicine
from app.core.security import get_password_hash
from app.enums import UserRole
from app.crud.crud_medicine import STANDARD_MEDICINES

def seed_initial_data():
    """Seed initial demo accounts and standard medicines on startup."""
    db = SessionLocal()
    try:
        # 1. Seed Initial Accounts
        initial_users = [
            {
                "email": "doctor@rxbridge.com",
                "password": "doctor123",
                "role": UserRole.DOCTOR.value,
                "doctor_name": "Dr. Ravi Sharma",
                "reg_no": "MH-12345 (MMC)",
                "qualification": "MBBS, MD (Medicine)",
                "clinic_name": "Shripal Care Hospital & Clinic",
                "clinic_address": "Station Road, Mumbai, Maharashtra 400001",
                "clinic_phone": "+91 98200 12345",
            },
            {
                "email": "staff@rxbridge.com",
                "password": "staff123",
                "role": UserRole.STAFF.value,
            },
            {
                "email": "pharmacy@rxbridge.com",
                "password": "pharmacy123",
                "role": UserRole.PHARMACY.value,
            },
        ]

        for u in initial_users:
            existing = db.query(User).filter(User.email == u["email"]).first()
            if not existing:
                user = User(
                    email=u["email"],
                    hashed_password=get_password_hash(u["password"]),
                    role=u["role"],
                    doctor_name=u.get("doctor_name"),
                    reg_no=u.get("reg_no"),
                    qualification=u.get("qualification"),
                    clinic_name=u.get("clinic_name"),
                    clinic_address=u.get("clinic_address"),
                    clinic_phone=u.get("clinic_phone"),
                )
                db.add(user)

        # 2. Seed initial medicines into custom_medicines master if table is empty
        med_count = db.query(CustomMedicine).count()
        if med_count == 0:
            for sm in STANDARD_MEDICINES[:30]:  # Seed top standard medicines
                cm = CustomMedicine(
                    name=sm["name"],
                    dose=sm.get("dose", ""),
                    duration=sm.get("duration", "")
                )
                db.add(cm)

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[Startup Warning] Seeding failed or already complete: {e}")
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure tables exist
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"[Lifespan Warning] Table creation skipped: {e}")

    # Ensure uploads directory exists
    try:
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    except Exception:
        pass

    # Seed initial data
    try:
        seed_initial_data()
    except Exception as e:
        print(f"[Lifespan Warning] Seed skipped: {e}")

    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for RxBridge Digital Prescription System",
    version="1.0.0",
    lifespan=lifespan
)

# Security Middlewares
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static uploads safely
try:
    upload_path = "/tmp/uploads" if os.name != "nt" and not os.access(".", os.W_OK) else "uploads"
    os.makedirs(os.path.join(upload_path, "lab_reports"), exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=upload_path), name="uploads")
except Exception as e:
    print(f"[Mount Warning] Could not mount uploads: {e}")

# Mount frontend static app
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))
if os.path.exists(frontend_dir):
    app.mount("/frontend", StaticFiles(directory=frontend_dir, html=True), name="frontend")

# Include Routers
api_v1 = settings.API_V1_STR
app.include_router(auth_router, prefix=api_v1)
app.include_router(prescription_router, prefix=api_v1)
app.include_router(patient_router, prefix=api_v1)
app.include_router(medicine_router, prefix=api_v1)
app.include_router(pharmacy_router, prefix=api_v1)
app.include_router(upload_router, prefix=api_v1)
app.include_router(dashboard_router, prefix=api_v1)
app.include_router(verify_router, prefix=api_v1)
app.include_router(agent_router, prefix=api_v1)

@app.get("/")
def root():
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "docs": "/docs",
        "frontend": "/frontend/index.html",
        "verify": "/frontend/verify.html",
        "version": "1.0.0"
    }

@app.get("/health")
@app.get("/api/health")
@app.get("/api/v1/health")
def health():
    return {"status": "healthy"}

handler = app

from app.routes.auth_routes import router as auth_router
from app.routes.prescription_routes import router as prescription_router
from app.routes.patient_routes import router as patient_router
from app.routes.medicine_routes import router as medicine_router
from app.routes.pharmacy_routes import router as pharmacy_router
from app.routes.upload_routes import router as upload_router
from app.routes.dashboard_routes import router as dashboard_router
from app.routes.verify_routes import router as verify_router
from app.routes.agent_routes import router as agent_router

__all__ = [
    "auth_router",
    "prescription_router",
    "patient_router",
    "medicine_router",
    "pharmacy_router",
    "upload_router",
    "dashboard_router",
    "verify_router",
    "agent_router",
]

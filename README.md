# RxBridge – Digital Prescription & Clinic Management System

RxBridge is a secure, modern digital prescription and patient intake system for clinics and hospitals, modeled after enterprise FastAPI standards. It eliminates illegibility errors, maintains longitudinal patient medical records, provides automated BMI calculation and vitals validation, and enforces strict role-based access for Doctors, Nursing Staff, and Pharmacy.

---

## 🏗️ Architecture & Project Structure

The project separates the presentation layer (`frontend/`) and the backend service layer (`backend/`), with database migrations version-controlled via Alembic and environment secrets isolated in `.env`.

```text
pharmacy/
├── .gitignore                          # Root git ignore (ignores .env, cache, logs)
├── README.md                           # Documentation & setup guide
├── RxBridge_BRD.pdf                    # Business Requirements Document
│
├── frontend/                           # Presentation Layer (Vanilla JS + HTML5 + CSS3)
│   ├── index.html                      # Clinic web app (Doctor, Staff, Pharmacy)
│   ├── verify.html                     # QR code verification portal
│   ├── css/
│   │   └── style.css                   # Custom theme, responsive styling, print styles
│   └── js/
│       ├── api.js                      # REST API client with JWT handling
│       └── app.js                      # UI controller, autocomplete, charts, PDF export
│
└── backend/                            # Application Layer (FastAPI + SQLAlchemy + MySQL)
    ├── .env                            # Local environment configuration (git-ignored)
    ├── .env.example                    # Safe template for production/development
    ├── .gitignore                      # Backend-specific ignore rules
    ├── requirements.txt                # Python dependencies
    ├── alembic.ini                     # Alembic configuration
    ├── alembic/                        # Database migration scripts
    │   ├── env.py                      # Dynamic migration environment
    │   ├── script.py.mako
    │   └── versions/                   # Migration versions
    │       └── 526e79384f80_create_initial_tables.py
    └── app/
        ├── __init__.py
        ├── main.py                     # FastAPI application setup, CORS & lifespan seeding
        ├── dependencies.py             # Auth & Role dependencies (require_doctor, etc.)
        ├── enums.py                    # UserRole, PrescriptionStatus, MedicineFrequency
        ├── core/
        │   ├── config.py               # Pydantic Settings loaded from .env
        │   ├── security.py             # Bcrypt password hashing & JWT encoding/decoding
        │   └── role_checker.py         # Role verification guard
        ├── db/
        │   ├── base.py                 # SQLAlchemy Declarative Base
        │   ├── database.py             # Engine, SessionLocal, get_db session generator
        │   └── models/                 # SQLAlchemy ORM Models
        │       ├── user.py             # Users & doctor letterhead profile
        │       ├── patient.py          # Patients & consent preferences
        │       ├── prescription.py     # Prescriptions, vitals & doctor snapshot
        │       ├── medicine.py         # Prescription medicines & custom master list
        │       ├── lab_report.py       # Patient lab report JPG records
        │       └── audit_log.py        # System audit trail (logins, creates, dispenses)
        ├── schemas/                    # Pydantic request & response validation
        │   ├── user.py
        │   ├── prescription.py
        │   ├── medicine.py
        │   └── lab_report.py
        ├── crud/                       # Database repository layer
        │   ├── crud_user.py
        │   ├── crud_prescription.py
        │   ├── crud_patient.py
        │   ├── crud_medicine.py
        │   └── crud_audit.py
        └── routes/                     # FastAPI API Routers
            ├── auth_routes.py          # /api/v1/auth (login, register, me, settings)
            ├── prescription_routes.py  # /api/v1/prescriptions (intake, complete, queue, history)
            ├── patient_routes.py       # /api/v1/patients (mobile lookup, timeline)
            ├── medicine_routes.py      # /api/v1/medicines (autocomplete, master list)
            ├── pharmacy_routes.py      # /api/v1/pharmacy (consented prescriptions, dispense)
            ├── upload_routes.py        # /api/v1/uploads (lab reports)
            ├── dashboard_routes.py     # /api/v1/dashboard (clinic analytics)
            └── verify_routes.py        # /api/v1/verify (public verification)
```

---

## 🔑 Initial Demo User Accounts

When the backend starts up, it automatically initializes the following accounts:

| Role | Username / Email | Password | Permissions & Views |
| :--- | :--- | :--- | :--- |
| **Doctor** | `doctor@rxbridge.com` | `doctor123` | Waiting queue, Write prescription, Patient longitudinal history, Dashboard stats, Letterhead settings, Delete Rx |
| **Nursing / Staff** | `staff@rxbridge.com` | `staff123` | Patient intake (vitals, BMI, consent, lab report JPG upload), Send to doctor queue, View clinic completed history |
| **Pharmacy** | `pharmacy@rxbridge.com` | `pharmacy123` | Strictly view/dispense prescriptions where patient checked **"Pharmacy offers & promotions"** |

*(Quick demo buttons are also embedded on the login page for one-click testing.)*

---

## 🗄️ Database Tables (MySQL)

- **`users`**: Email, bcrypt hashed password, user role (`doctor`, `staff`, `pharmacy`), doctor letterhead info (name, registration number, qualification, clinic details, signature base64).
- **`patients`**: Normalized 10-digit mobile number, full name, age/gender, latest recorded consent (`offers`, `refill`).
- **`prescriptions`**: Unique Rx number (`RX-YYYYMMDD-XXXX`), patient demographics, vitals strip (`bp_sys`, `bp_dia`, `pulse`, `temperature`, `spo2`, `respiratory_rate`, `height`, `bmi`, `sugar`), diagnosis, advice, follow-up, status (`intake`, `completed`, `dispensed`), doctor letterhead snapshot (frozen at issue).
- **`prescription_medicines`**: Prescribed items linked to a prescription (name, dose, duration, frequency, food relation, timing).
- **`custom_medicines`**: Self-learning master catalog learned from doctor prescriptions and standard Indian medicines.
- **`lab_reports`**: Lab report image uploads (JPG/PNG, up to 10MB) linked by patient mobile.
- **`audit_logs`**: Immutable security trail of logins, intakes, prescriptions, dispensing, and deletions.

---

## 🚀 Running the Project

### 1. Start the Backend API
Navigate to the `backend` directory and run:

```powershell
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- **Interactive API Documentation (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Alternative ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Integrated Frontend**: [http://localhost:8000/frontend/index.html](http://localhost:8000/frontend/index.html)
- **Prescription Verification**: [http://localhost:8000/frontend/verify.html](http://localhost:8000/frontend/verify.html)

### 2. Database Migrations (Alembic)
If you update any models in `backend/app/db/models/`, run:

```powershell
cd backend
alembic revision --autogenerate -m "describe_changes"
alembic upgrade head
```

### 3. Frontend Development
You can either open `frontend/index.html` directly using VSCode **Live Server** (`http://127.0.0.1:5500`) or access it served directly through FastAPI at [http://localhost:8000/frontend/index.html](http://localhost:8000/frontend/index.html). CORS is enabled out of the box.

from enum import Enum

class UserRole(str, Enum):
    DOCTOR = "doctor"
    STAFF = "staff"
    PHARMACY = "pharmacy"

class PrescriptionStatus(str, Enum):
    INTAKE = "intake"
    COMPLETED = "completed"
    DISPENSED = "dispensed"

class MedicineFrequency(str, Enum):
    OD = "OD"
    BD = "BD"
    TDS = "TDS"
    QID = "QID"
    SOS = "SOS"
    STAT = "STAT"
    HS = "HS"

class FoodRelation(str, Enum):
    BEFORE_FOOD = "Before food"
    AFTER_FOOD = "After food"
    EMPTY_STOMACH = "Empty stomach"

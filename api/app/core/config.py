import os
from typing import List, Union
from pydantic_settings import BaseSettings
from pydantic import field_validator

class Settings(BaseSettings):
    PROJECT_NAME: str = "Pharma Bridge - Digital Prescription & Fulfillment Platform"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    
    # Database
    DATABASE_URL: str = "mysql+pymysql://root:Reynolds%4008@localhost:3306/rxbridge_db"
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800
    
    # JWT & Auth
    JWT_SECRET: str = "rxbridge-jwt-secret-key-2026-super-secure-production-grade"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    
    # CORS
    ALLOWED_ORIGINS: Union[str, List[str]] = "http://localhost:5500,http://127.0.0.1:5500,http://localhost:3000,http://127.0.0.1:8000,http://localhost:8000,*"
    
    # Uploads
    CLOUDINARY_CLOUD: str = "yrkeqdag"
    CLOUDINARY_PRESET: str = "rxbridge_reports"
    UPLOAD_DIR: str = "uploads/lab_reports"

    # AI Assistant Settings (Dual Keys + Failover)
    GROQ_API_KEY_1: str = ""
    GROQ_API_KEY_2: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-120b"


    @property
    def cors_origins(self) -> List[str]:
        if isinstance(self.ALLOWED_ORIGINS, list):
            return self.ALLOWED_ORIGINS
        if isinstance(self.ALLOWED_ORIGINS, str):
            if self.ALLOWED_ORIGINS.strip() == "*":
                return ["*"]
            return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]
        return ["*"]

    class Config:
        env_file = (
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "backend", ".env"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"),
            "backend/.env",
            ".env"
        )
        extra = "ignore"

settings = Settings()

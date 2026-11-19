import certifi
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

db_url = settings.DATABASE_URL
if "tidbcloud.com" in db_url.lower() and "/sys" in db_url:
    db_url = db_url.replace("/sys", "/rxbridge_db")

connect_args = {}
if "tidbcloud.com" in db_url.lower() or "ssl" in db_url.lower():
    ca_path = certifi.where()
    connect_args["ssl_ca"] = ca_path
    connect_args["ssl_verify_cert"] = True
    connect_args["ssl_verify_identity"] = True
    connect_args["ssl"] = {"ca": ca_path}

engine = create_engine(
    db_url,
    echo=False,
    pool_pre_ping=True,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

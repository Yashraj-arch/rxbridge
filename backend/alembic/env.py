from logging.config import fileConfig
import sys
import certifi
from os.path import abspath, dirname

from sqlalchemy import create_engine, pool
from alembic import context

# Add backend directory to sys.path
sys.path.insert(0, dirname(dirname(abspath(__file__))))

from app.core.config import settings
from app.db.base import Base
import app.db.models  # Registers all models

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    connect_args = {}
    if "tidbcloud.com" in settings.DATABASE_URL.lower() or "ssl" in settings.DATABASE_URL.lower():
        connect_args["ssl"] = {"ca": certifi.where()}

    connectable = create_engine(
        settings.DATABASE_URL,
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

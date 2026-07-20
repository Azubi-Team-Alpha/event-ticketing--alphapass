from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool, text
from alembic import context
import os
import sys

# make sure app is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.db.base import Base
from app.models.models import (
    Admin, Organizer, EventCategory, Event, TicketType, PromoCode,
    Order, OrderItem, Ticket, TicketTransfer, ResaleListing,
    OrganizerPayout, PlatformSettings, AuditLog
)

from app.core.config import settings

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = settings.DATABASE_URL
    is_sqlite = url.startswith("sqlite")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        version_table_schema=None if is_sqlite else settings.DB_SCHEMA,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = settings.DATABASE_URL
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        is_sqlite = connection.dialect.name == "sqlite"
        if connection.dialect.name == "postgresql":
            connection.execute(text(
                f'CREATE SCHEMA IF NOT EXISTS {settings.DB_SCHEMA} AUTHORIZATION CURRENT_USER'
            ))
            connection.execute(text(
                f'SET search_path TO {settings.DB_SCHEMA}, public'
            ))
            connection.commit()

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema=None if is_sqlite else settings.DB_SCHEMA,
        )
        with context.begin_transaction():
            context.run_migrations()



if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

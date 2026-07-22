"""
db/base.py – Legacy SQLAlchemy shim kept for test compatibility only.

Production code (all routers) uses app.db.dynamodb.dynamodb_helper exclusively.
This file is imported only by the test suite conftest.py via SQLite.
DO NOT add new production code here.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Default to an in-memory SQLite for local/test environments.
# In Lambda, this module is imported by conftest but never called at runtime.
_DEFAULT_DB = "sqlite:///./test.db"

import os
_DATABASE_URL = os.environ.get("DATABASE_URL", _DEFAULT_DB)

if _DATABASE_URL.startswith("sqlite"):
    engine = create_engine(_DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(_DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """SQLAlchemy session dependency – used ONLY by the test suite."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
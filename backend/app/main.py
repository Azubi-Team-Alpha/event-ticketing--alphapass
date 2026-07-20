from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.core.config import settings
from app.db.base import Base, engine

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    description="Event Ticketing Platform API – supports organizers, admins, and guest checkout.",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def bootstrap_database() -> None:
    if engine.dialect.name == "postgresql":
        with engine.begin() as connection:
            connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {settings.DB_SCHEMA}"))

    # Import models so SQLAlchemy registers them before create_all.
    from app.models import models  # noqa: F401
    Base.metadata.create_all(bind=engine)


# ── Routers ───────────────────────────────────────────────────────────────────
from app.routers import health, auth, events, tickets, orders, transfers, resale, checkin, organizer, admin  # noqa: E402

app.include_router(health.router,     tags=["Health"])
app.include_router(auth.router,       prefix="/auth",      tags=["Auth"])
app.include_router(events.router,     prefix="/events",    tags=["Events"])
app.include_router(tickets.router,    prefix="/tickets",   tags=["Tickets"])
app.include_router(orders.router,     prefix="/orders",    tags=["Orders"])
app.include_router(transfers.router,  prefix="/transfers", tags=["Transfers"])
app.include_router(resale.router,     prefix="/resale",    tags=["Resale"])
app.include_router(checkin.router,    prefix="/checkin",   tags=["Check-in"])
app.include_router(organizer.router,  prefix="/organizer", tags=["Organizer"])
app.include_router(admin.router,      prefix="/admin",     tags=["Admin"])
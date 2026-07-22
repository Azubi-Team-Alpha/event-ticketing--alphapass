from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    description="AlphaPass Event Ticketing Platform API – Serverless DynamoDB architecture.",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
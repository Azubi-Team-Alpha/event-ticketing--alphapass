from fastapi import FastAPI, Response
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
# NOTE: allow_credentials must be False when allow_origins=["*"]; browsers
# reject credentialed requests to wildcard origins per the CORS spec.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Amz-Date", "X-Api-Key",
                   "X-Amz-Security-Token", "Accept", "Origin"],
    expose_headers=["*"],
)


# ── Routers ───────────────────────────────────────────────────────────────────
# Routers are included BEFORE the catch-all OPTIONS handler so that
# router-specific routes take priority, and the catch-all only handles
# any path not matched by a router.
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


# ── Catch-all OPTIONS handler (preflight fallback) ────────────────────────────
# Registered LAST so it only matches paths not handled by any router above.
# API Gateway's MOCK integration should intercept OPTIONS before Lambda
# is invoked, but this handler ensures CORS headers are present even if
# OPTIONS reaches the Lambda function (e.g. during local development).
@app.options("/{full_path:path}")
def options_handler(full_path: str):
    """Fallback handler for preflight OPTIONS requests not matched by a router."""
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Amz-Date, X-Api-Key, X-Amz-Security-Token, Accept, Origin",
        },
    )
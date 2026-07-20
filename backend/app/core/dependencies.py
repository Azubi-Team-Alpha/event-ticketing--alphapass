"""
Ticket Hub – FastAPI dependency injectors.
Supports three authenticated roles: Admin, Organizer.
Guest routes have no dependency (or use optional_auth).
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError

from app.db.base import get_db
from app.models.models import Admin, Organizer
from app.core.security import decode_access_token

bearer_scheme   = HTTPBearer(auto_error=True)
optional_bearer = HTTPBearer(auto_error=False)


# ── Admin ─────────────────────────────────────────────────────────────────────

def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Admin:
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    admin = db.query(Admin).filter(Admin.id == payload["sub"]).first()
    if not admin or not admin.is_active:
        raise HTTPException(status_code=401, detail="Admin account not found or inactive")
    return admin


def get_super_admin(admin: Admin = Depends(get_current_admin)) -> Admin:
    if not admin.is_super:
        raise HTTPException(status_code=403, detail="Super-admin access required")
    return admin


# ── Organizer ─────────────────────────────────────────────────────────────────

def get_current_organizer(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Organizer:
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if payload.get("role") != "organizer":
        raise HTTPException(status_code=403, detail="Organizer access required")

    organizer = db.query(Organizer).filter(Organizer.id == payload["sub"]).first()
    if not organizer:
        raise HTTPException(status_code=401, detail="Organizer not found")

    from app.models.models import OrganizerStatus
    if organizer.status == OrganizerStatus.suspended:
        raise HTTPException(status_code=403, detail="Organizer account is suspended")
    return organizer


def get_active_organizer(organizer: Organizer = Depends(get_current_organizer)) -> Organizer:
    """Requires organizer to be email-verified and active."""
    from app.models.models import OrganizerStatus
    if not organizer.email_verified:
        raise HTTPException(status_code=403, detail="Please verify your email first")
    if organizer.status not in (OrganizerStatus.active, OrganizerStatus.verified):
        raise HTTPException(
            status_code=403,
            detail="Your organizer account is pending admin approval"
        )
    return organizer


# ── Legacy shims ──────────────────────────────────────────────────────────────

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    """Legacy: returns Admin or Organizer depending on token role."""
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    role = payload.get("role")
    if role == "admin":
        obj = db.query(Admin).filter(Admin.id == payload["sub"]).first()
    elif role == "organizer":
        obj = db.query(Organizer).filter(Organizer.id == payload["sub"]).first()
    else:
        raise HTTPException(status_code=401, detail="Invalid token role")

    if not obj:
        raise HTTPException(status_code=401, detail="User not found")
    return obj


def get_admin_user(current=Depends(get_current_user)):
    """Legacy shim: checks if the resolved user is an Admin."""
    if not isinstance(current, Admin):
        raise HTTPException(status_code=403, detail="Admin access required")
    return current
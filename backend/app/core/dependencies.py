"""
AlphaPass – FastAPI dependency injectors for DynamoDB.
Supports three authenticated roles: Admin, Organizer, and CurrentUser.
"""
from typing import Any, Dict
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError

from app.db.dynamodb import dynamodb_helper
from app.core.security import decode_access_token

bearer_scheme   = HTTPBearer(auto_error=True)
optional_bearer = HTTPBearer(auto_error=False)


class AttrDict(dict):
    """Dict subclass allowing dot notation attribute access."""
    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError:
            raise AttributeError(f"'AttrDict' object has no attribute '{name}'")

    def __setattr__(self, name: str, value: Any) -> None:
        self[name] = value


# ── Admin ─────────────────────────────────────────────────────────────────────

def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> AttrDict:
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    admin_data = dynamodb_helper.get_admin(payload["sub"])
    if not admin_data or not admin_data.get("is_active", True):
        raise HTTPException(status_code=401, detail="Admin account not found or inactive")
    
    admin_dict = AttrDict(admin_data)
    admin_dict.id = admin_data.get("AdminID", payload["sub"])
    return admin_dict


def get_super_admin(admin: AttrDict = Depends(get_current_admin)) -> AttrDict:
    if not admin.get("is_super", False):
        raise HTTPException(status_code=403, detail="Super-admin access required")
    return admin


# ── Organizer ─────────────────────────────────────────────────────────────────

def get_current_organizer(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> AttrDict:
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if payload.get("role") != "organizer":
        raise HTTPException(status_code=403, detail="Organizer access required")

    org_data = dynamodb_helper.get_organizer(payload["sub"])
    if not org_data:
        raise HTTPException(status_code=401, detail="Organizer not found")

    if org_data.get("status") == "suspended":
        raise HTTPException(status_code=403, detail="Organizer account is suspended")
    
    org_dict = AttrDict(org_data)
    org_dict.id = org_data.get("OrganizerID", payload["sub"])
    return org_dict


def get_active_organizer(organizer: AttrDict = Depends(get_current_organizer)) -> AttrDict:
    """Requires organizer to be email-verified and active."""
    if not organizer.get("email_verified", False):
        raise HTTPException(status_code=403, detail="Please verify your email first")
    status = organizer.get("status")
    if status not in ("active", "verified"):
        raise HTTPException(
            status_code=403,
            detail="Your organizer account is pending admin approval"
        )
    return organizer


# ── Generic User ──────────────────────────────────────────────────────────────

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> AttrDict:
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    role = payload.get("role")
    sub = payload.get("sub")
    if role == "admin":
        data = dynamodb_helper.get_admin(sub)
        if data:
            data["id"] = data.get("AdminID", sub)
    elif role == "organizer":
        data = dynamodb_helper.get_organizer(sub)
        if data:
            data["id"] = data.get("OrganizerID", sub)
    else:
        raise HTTPException(status_code=401, detail="Invalid token role")

    if not data:
        raise HTTPException(status_code=401, detail="User not found")
    return AttrDict(data)


def get_admin_user(current: AttrDict = Depends(get_current_user)) -> AttrDict:
    if "AdminID" not in current:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current
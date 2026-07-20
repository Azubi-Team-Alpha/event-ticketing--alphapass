"""Auth router – Organizer + Admin authentication."""
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.models.models import Admin, Organizer, OrganizerStatus, AuditLog
from app.schemas.schemas import (
    AdminRegister, AdminLogin, AdminResponse,
    OrganizerRegister, OrganizerLogin, OrganizerResponse, OrganizerProfileUpdate,
    TokenResponse, PasswordResetRequest, PasswordReset, EmailVerification,
)
from app.core.security import hash_password, verify_password, create_access_token
from app.core.dependencies import get_current_admin, get_current_organizer, get_current_user
from app.core.config import settings

router = APIRouter()


def _log(db, actor_type, actor_id, actor_email, action, **meta):
    db.add(AuditLog(
        actor_type=actor_type, actor_id=actor_id,
        actor_email=actor_email, action=action, meta=meta or None,
    ))


# ── Admin Auth ────────────────────────────────────────────────────────────────

@router.post("/admin/signup", response_model=AdminResponse, status_code=201, tags=["Admin Auth"])
def admin_signup(body: AdminRegister, db: Session = Depends(get_db)):
    if db.query(Admin).filter(Admin.email == body.email).first():
        raise HTTPException(400, "Email already registered")
    admin_count = db.query(Admin).count()
    if admin_count > 0:
        expected = getattr(settings, "ADMIN_INVITE_CODE", None)
        if expected and body.invite_code != expected:
            raise HTTPException(403, "Invalid invite code")
    admin = Admin(
        email=body.email, full_name=body.full_name,
        password_hash=hash_password(body.password),
        is_super=(admin_count == 0), email_verified=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    _log(db, "admin", admin.id, admin.email, "admin.signup")
    db.commit()
    return admin


@router.post("/admin/login", response_model=TokenResponse, tags=["Admin Auth"])
def admin_login(body: AdminLogin, db: Session = Depends(get_db)):
    admin = db.query(Admin).filter(Admin.email == body.email).first()
    if not admin or not verify_password(body.password, admin.password_hash):
        raise HTTPException(401, "Invalid email or password")
    if not admin.is_active:
        raise HTTPException(403, "Admin account is deactivated")
    token = create_access_token(admin.id, role="admin")
    _log(db, "admin", admin.id, admin.email, "admin.login")
    db.commit()
    return TokenResponse(access_token=token, role="admin")


@router.get("/admin/me", response_model=AdminResponse, tags=["Admin Auth"])
def admin_me(admin: Admin = Depends(get_current_admin)):
    return admin


# ── Organizer Auth ────────────────────────────────────────────────────────────

@router.post("/organizer/signup", response_model=OrganizerResponse, status_code=201, tags=["Organizer Auth"])
def organizer_signup(body: OrganizerRegister, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    if db.query(Organizer).filter(Organizer.email == body.email).first():
        raise HTTPException(400, "Email already registered")
    token = secrets.token_urlsafe(32)
    org = Organizer(
        email=body.email, full_name=body.full_name,
        password_hash=hash_password(body.password),
        business_name=body.business_name, phone=body.phone,
        verification_token=token, status=OrganizerStatus.pending,
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    _log(db, "organizer", org.id, org.email, "organizer.signup")
    db.commit()
    background_tasks.add_task(_send_verification_email, org.email, org.full_name, token)
    return org


@router.post("/organizer/login", response_model=TokenResponse, tags=["Organizer Auth"])
def organizer_login(body: OrganizerLogin, db: Session = Depends(get_db)):
    org = db.query(Organizer).filter(Organizer.email == body.email).first()
    if not org or not verify_password(body.password, org.password_hash):
        raise HTTPException(401, "Invalid email or password")
    if org.status == OrganizerStatus.suspended:
        raise HTTPException(403, "Account suspended")
    token = create_access_token(org.id, role="organizer")
    _log(db, "organizer", org.id, org.email, "organizer.login")
    db.commit()
    return TokenResponse(access_token=token, role="organizer")


@router.get("/organizer/me", response_model=OrganizerResponse, tags=["Organizer Auth"])
def organizer_me(org: Organizer = Depends(get_current_organizer)):
    return org


@router.put("/organizer/me", response_model=OrganizerResponse, tags=["Organizer Auth"])
def update_organizer_profile(
    body: OrganizerProfileUpdate, db: Session = Depends(get_db),
    org: Organizer = Depends(get_current_organizer),
):
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(org, field, value)
    db.commit()
    db.refresh(org)
    return org


# ── Email Verification ────────────────────────────────────────────────────────

@router.post("/verify-email", tags=["Auth"])
def verify_email(body: EmailVerification, db: Session = Depends(get_db)):
    org = db.query(Organizer).filter(Organizer.verification_token == body.token).first()
    if not org:
        raise HTTPException(400, "Invalid or expired verification token")
    org.email_verified = True
    org.verification_token = None
    if org.status == OrganizerStatus.pending:
        org.status = OrganizerStatus.active if not settings.REQUIRE_EVENT_APPROVAL else OrganizerStatus.verified
    db.commit()
    return {"message": "Email verified successfully"}


# ── Password Reset ────────────────────────────────────────────────────────────

@router.post("/request-password-reset", tags=["Auth"])
def request_password_reset(body: PasswordResetRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    org = db.query(Organizer).filter(Organizer.email == body.email).first()
    if org:
        token = secrets.token_urlsafe(32)
        org.reset_token = token
        org.reset_token_expires = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=settings.PASSWORD_RESET_EXPIRE_HOURS)
        db.commit()
        background_tasks.add_task(_send_reset_email, org.email, org.full_name, token)
    return {"message": "If that email exists, a reset link has been sent"}


@router.post("/reset-password", tags=["Auth"])
def reset_password(body: PasswordReset, db: Session = Depends(get_db)):
    org = db.query(Organizer).filter(Organizer.reset_token == body.token).first()
    if not org or (org.reset_token_expires and org.reset_token_expires < datetime.now(timezone.utc).replace(tzinfo=None)):
        raise HTTPException(400, "Invalid or expired reset token")
    org.password_hash = hash_password(body.new_password)
    org.reset_token = None
    org.reset_token_expires = None
    db.commit()
    return {"message": "Password reset successfully"}


# ── Unified & Compatibility Endpoints ─────────────────────────────────────────

@router.post("/login", response_model=TokenResponse, tags=["Auth"])
def unified_login(body: AdminLogin, db: Session = Depends(get_db)):
    # 1. Try Admin
    admin = db.query(Admin).filter(Admin.email == body.email).first()
    if admin and verify_password(body.password, admin.password_hash):
        if not admin.is_active:
            raise HTTPException(403, "Admin account is deactivated")
        token = create_access_token(admin.id, role="admin")
        _log(db, "admin", admin.id, admin.email, "admin.login")
        db.commit()
        return TokenResponse(access_token=token, role="admin")

    # 2. Try Organizer
    org = db.query(Organizer).filter(Organizer.email == body.email).first()
    if org and verify_password(body.password, org.password_hash):
        if org.status == OrganizerStatus.suspended:
            raise HTTPException(403, "Account suspended")
        token = create_access_token(org.id, role="organizer")
        _log(db, "organizer", org.id, org.email, "organizer.login")
        db.commit()
        return TokenResponse(access_token=token, role="organizer")

    raise HTTPException(401, "Invalid email or password")


@router.post("/register", response_model=OrganizerResponse, status_code=201, tags=["Auth"])
def unified_register(body: OrganizerRegister, db: Session = Depends(get_db)):
    if db.query(Organizer).filter(Organizer.email == body.email).first():
        raise HTTPException(400, "Email already registered")
    org = Organizer(
        email=body.email, full_name=body.full_name,
        password_hash=hash_password(body.password),
        email_verified=True, status=OrganizerStatus.active,
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    _log(db, "organizer", org.id, org.email, "organizer.signup")
    db.commit()
    return org


@router.get("/me", tags=["Auth"])
def get_me(current_user = Depends(get_current_user)):
    is_admin = isinstance(current_user, Admin)
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "is_admin": is_admin,
        "created_at": current_user.created_at,
    }



# ── Background email helpers ──────────────────────────────────────────────────

def _send_verification_email(email: str, name: str, token: str):
    try:
        from app.core.email import send_email
        url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
        html = (f"<h2>Welcome, {name}!</h2>"
                f'<p>Verify your Ticket Hub organizer account:</p>'
                f'<a href="{url}" style="background:#6366f1;color:#fff;padding:12px 24px;'
                f'border-radius:6px;text-decoration:none;">Verify Email</a>')
        send_email(email, "Verify your Ticket Hub account", html)
    except Exception as e:
        print(f"[EMAIL] verification failed for {email}: {e}")


def _send_reset_email(email: str, name: str, token: str):
    try:
        from app.core.email import send_email
        url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
        html = (f"<h2>Password Reset</h2><p>Hi {name},</p>"
                f'<a href="{url}" style="background:#6366f1;color:#fff;padding:12px 24px;'
                f'border-radius:6px;text-decoration:none;">Reset Password</a>')
        send_email(email, "Reset your Ticket Hub password", html)
    except Exception as e:
        print(f"[EMAIL] reset failed for {email}: {e}")

from __future__ import annotations

import secrets
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user, rate_limit
from app.core.config import get_settings
from app.core.errors import AppError, Conflict, NotFound, Unauthorized
from app.core.security import COOKIE_NAME, create_access_token, hash_password, verify_password
from app.db.models import User
from app.db.session import get_db
from app.schemas.api import LoginIn, RegisterIn

router = APIRouter(prefix="/auth", tags=["auth"])
auth_limit = rate_limit("auth", get_settings().rate_limit_auth_per_minute)


def _issue(response: Response, user: User) -> dict:
    s = get_settings()
    token = create_access_token(user.id)
    response.set_cookie(COOKIE_NAME, token, httponly=True, secure=s.cookie_secure, samesite="lax",
                        max_age=s.access_token_expire_minutes * 60, path="/")
    return {"access_token": token, "token_type": "bearer",
            "user": {"id": user.id, "email": user.email, "name": user.name, "is_demo": user.is_demo}}


@router.post("/register", dependencies=[Depends(auth_limit)])
def register(data: RegisterIn, response: Response, db: Session = Depends(get_db)):
    email = data.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise Conflict("An account with this email already exists.")
    user = User(email=email, name=data.name.strip(), password_hash=hash_password(data.password))
    db.add(user)
    db.commit()
    return _issue(response, user)


@router.post("/login", dependencies=[Depends(auth_limit)])
def login(data: LoginIn, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == data.email.lower()))
    if not user or not verify_password(data.password, user.password_hash):
        raise Unauthorized("Email or password is incorrect.")
    return _issue(response, user)


@router.post("/demo", dependencies=[Depends(auth_limit)])
def demo_login(response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.is_demo.is_(True)))
    if not user:
        raise NotFound("The demo account isn't available.")
    return _issue(response, user)


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(current_user)):
    return {"id": user.id, "email": user.email, "name": user.name, "is_demo": user.is_demo,
            "onboarding_completed": bool(user.profile and user.profile.onboarding_completed)}


@router.get("/providers")
def providers():
    s = get_settings()
    return {"password": True, "google": bool(s.google_client_id and s.google_client_secret)}


# ------------------------------------------------------------------------ Google OAuth
GOOGLE_AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO = "https://openidconnect.googleapis.com/v1/userinfo"


@router.get("/oauth/google/login")
def google_login():
    s = get_settings()
    if not (s.google_client_id and s.google_client_secret):
        raise NotFound("Google sign-in isn't configured.")
    state = secrets.token_urlsafe(24)
    params = {"client_id": s.google_client_id, "redirect_uri": s.oauth_redirect_url, "response_type": "code",
              "scope": "openid email profile", "state": state, "prompt": "select_account"}
    resp = RedirectResponse(f"{GOOGLE_AUTH}?{urlencode(params)}")
    resp.set_cookie("pf_oauth_state", state, httponly=True, secure=s.cookie_secure, samesite="lax", max_age=600)
    return resp


@router.get("/oauth/google/callback")
def google_callback(request: Request, code: str, state: str, db: Session = Depends(get_db)):
    s = get_settings()
    if not state or state != request.cookies.get("pf_oauth_state"):
        raise Unauthorized("Sign-in session expired. Please try again.")
    try:
        with httpx.Client(timeout=10) as client:
            tok = client.post(GOOGLE_TOKEN, data={"code": code, "client_id": s.google_client_id, "client_secret": s.google_client_secret,
                                                  "redirect_uri": s.oauth_redirect_url, "grant_type": "authorization_code"})
            tok.raise_for_status()
            info = client.get(GOOGLE_USERINFO, headers={"Authorization": f"Bearer {tok.json()['access_token']}"})
            info.raise_for_status()
            profile = info.json()
    except httpx.HTTPError as exc:
        raise AppError("Google sign-in failed. Please try again.", code="oauth_failed", status_code=502) from exc
    if not profile.get("email_verified"):
        raise Unauthorized("Your Google email isn't verified.")
    email = profile["email"].lower()
    user = db.scalar(select(User).where(User.email == email))
    if not user:
        user = User(email=email, name=profile.get("name", ""), auth_provider="google")
        db.add(user)
        db.commit()
    resp = RedirectResponse(f"{s.frontend_url}/app")
    _issue(resp, user)
    resp.delete_cookie("pf_oauth_state")
    return resp


@router.post("/demo/reset")
def demo_reset(response: Response, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Restore the demo account to its original state (demo account only)."""
    from app.knowledge.catalog import get_catalog
    from app.seed import reset_demo_user

    if not user.is_demo:
        raise AppError("Only the demo account can be reset.", code="not_demo", status_code=403)
    fresh = reset_demo_user(db, get_catalog())
    return _issue(response, fresh)

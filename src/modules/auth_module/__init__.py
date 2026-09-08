"""
Auth module — session pages & authentication API.

Migrated from main.py (WS0.3, strangler step 1): register/login/logout,
auth.html page, Google direct OAuth flow, /auth/me. Public paths declared
in the module registration — no behavior changes, same URLs.
"""
import secrets
import time
from datetime import datetime, timezone
from typing import Dict, Optional
from urllib.parse import quote, urlencode

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel

from src.config import settings
from src.core.auth import (
    create_session_token,
    verify_session_token,
    user_store,
    auth_limiter,
    SESSION_COOKIE_NAME,
    SESSION_TTL_SECONDS,
)
from src.core.http_utils import safe_error, TEMPLATES_DIR
from src.core.logger import logger
from src.core.modules import module_registry
from src.core.supabase_client import supabase_db

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
GOOGLE_OAUTH_SCOPES = "openid email profile"
_google_oauth_states: Dict[str, float] = {}  # state -> created_at (CSRF, 10-min TTL)

_registration_cap = 500      # WS-B: raised from 50 (owner approval, pre-Phase 9)
LEGAL_TERMS_VERSION = "2026-09-08"  # keep in sync with src/modules/legal/__init__.py


class RegisterPayload(BaseModel):
    email: str
    password: str
    phone: Optional[str] = None
    full_name: Optional[str] = None
    terms_accepted: bool = False  # WS-B consent gate: MUST be true (client checkbox)


class LoginPayload(BaseModel):
    email: str
    password: str


def _set_session_cookie(resp, token: str):
    resp.set_cookie(
        SESSION_COOKIE_NAME, token,
        max_age=SESSION_TTL_SECONDS, httponly=True, samesite="lax",
        secure=(settings.APP_ENV.lower() == "production"),
    )


def register_router(app: FastAPI) -> None:
    # NOTE: /login + /register HTML pages moved to the pages module (WS0.3)
    # so auth.html goes through the unified template pipeline. This module
    # owns the auth API + Google OAuth only.

    @app.post("/auth/register", tags=["Auth"])
    async def register_user(payload: RegisterPayload, request: Request):
        """Creates a new account. First-ever user becomes admin (owner)."""
        client_ip = request.client.host if request.client else "unknown"
        if auth_limiter.is_blocked(f"reg:{client_ip}"):
            raise HTTPException(status_code=429, detail="محاولات كثيرة — انتظر 5 دقائق")

        if len(payload.password) < 8:
            raise HTTPException(status_code=400, detail="كلمة المرور يجب أن تكون 8 أحرف على الأقل")
        if "@" not in payload.email or "." not in payload.email:
            raise HTTPException(status_code=400, detail="البريد الإلكتروني غير صالح")
        if not payload.terms_accepted:
            raise HTTPException(
                status_code=400,
                detail="يجب الموافقة على شروط الاستخدام وسياسة الخصوصية قبل إنشاء الحساب"
            )
        if user_store.count() >= _registration_cap:
            raise HTTPException(status_code=403, detail="التسجيل مغلق حالياً")

        auth_limiter.record(f"reg:{client_ip}")
        try:
            user = user_store.create_user(
                email=payload.email,
                password=payload.password,
                phone=payload.phone,
                full_name=payload.full_name,
                terms_accepted_at=datetime.now(timezone.utc).isoformat(),
                terms_version=LEGAL_TERMS_VERSION,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=safe_error(e))

        token = create_session_token(user["id"], user.get("role", "user"), user["email"])
        resp = JSONResponse({"status": "success", "role": user.get("role", "user")})
        _set_session_cookie(resp, token)
        return resp

    @app.post("/auth/login", tags=["Auth"])
    async def login_user(payload: LoginPayload, request: Request):
        """Authenticates a user and issues a signed session cookie."""
        client_ip = request.client.host if request.client else "unknown"
        if auth_limiter.is_blocked(f"login:{client_ip}"):
            raise HTTPException(status_code=429, detail="محاولات كثيرة — انتظر 5 دقائق")

        user = user_store.authenticate(payload.email, payload.password)
        if not user:
            auth_limiter.record(f"login:{client_ip}")
            raise HTTPException(status_code=401, detail="البريد الإلكتروني أو كلمة المرور غير صحيحة")

        token = create_session_token(user["id"], user.get("role", "user"), user["email"])
        resp = JSONResponse({"status": "success", "role": user.get("role", "user")})
        _set_session_cookie(resp, token)
        return resp

    @app.post("/auth/logout", tags=["Auth"])
    async def logout_user():
        """Clears the session cookie."""
        resp = JSONResponse({"status": "success"})
        resp.delete_cookie(SESSION_COOKIE_NAME)
        return resp

    # ------------------------------------------------------------------
    # Google Sign-In — DIRECT OAuth from our backend (no Supabase hosted flow).
    # ------------------------------------------------------------------
    def _google_oauth_creds_ok() -> bool:
        return bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)

    def _persist_oauth_state(state: str, created_at: float):
        _google_oauth_states[state] = created_at
        try:
            supabase_db.set_setting("google_oauth_states", {
                "states": {state: created_at},
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
        except Exception as e:
            logger.warning(f"Could not persist OAuth state to Supabase (memory-only): {e}")

    def _consume_oauth_state(state: str) -> Optional[float]:
        now = time.time()
        for s in [s for s, t in _google_oauth_states.items() if now - t >= 600]:
            _google_oauth_states.pop(s, None)
        created = _google_oauth_states.pop(state, None)
        if created is None:
            try:
                payload = supabase_db.get_setting("google_oauth_states") or {}
                stored = payload.get("states", {}) if isinstance(payload, dict) else {}
                if state in stored:
                    created = float(stored[state])
                    try:
                        supabase_db.set_setting("google_oauth_states", {"states": {}, "updated_at": datetime.now(timezone.utc).isoformat()})
                    except Exception:
                        pass
            except Exception:
                return None
        if created is None or (now - created) >= 600:
            return None
        return created

    @app.get("/auth/google", tags=["Auth"])
    async def google_oauth_start(request: Request):
        """Redirects the browser STRAIGHT to Google's consent screen with OUR
        redirect_uri (APP_BASE_URL/auth/google/callback) so the consent screen
        shows our own domain — not Supabase's project ref."""
        if not _google_oauth_creds_ok():
            raise HTTPException(status_code=503, detail="تسجيل الدخول بجوجل غير مفعّل بعد — GOOGLE_CLIENT_ID/SECRET غير مضبوطين")
        now = time.time()
        for s in [s for s, t in _google_oauth_states.items() if now - t >= 600]:
            _google_oauth_states.pop(s, None)
        state = secrets.token_urlsafe(24)
        _persist_oauth_state(state, now)
        redirect_uri = f"{settings.APP_BASE_URL.rstrip('/')}/auth/google/callback"
        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": GOOGLE_OAUTH_SCOPES,
            "state": state,
            "prompt": "select_account",
        }
        url = f"{GOOGLE_AUTH_URL}?{urlencode(params, quote_via=quote)}"
        return RedirectResponse(url=url, status_code=303)

    @app.get("/auth/google/callback", tags=["Auth"])
    async def google_oauth_callback(request: Request):
        """Google redirects here with ?code&state. We validate the CSRF state,
        exchange the code with Google directly, read the verified profile,
        find-or-create the local user, and issue our signed session cookie."""
        try:
            if not _google_oauth_creds_ok():
                raise HTTPException(status_code=503, detail="Google sign-in not configured")
            state = request.query_params.get("state") or ""
            code = request.query_params.get("code") or ""
            err = request.query_params.get("error")
            if err or not code or _consume_oauth_state(state) is None:
                logger.warning(f"Google OAuth callback rejected (error={err or 'none'}, state_valid={bool(state)})")
                return RedirectResponse(url="/login?google=error", status_code=303)

            redirect_uri = f"{settings.APP_BASE_URL.rstrip('/')}/auth/google/callback"
            async with httpx.AsyncClient(timeout=15.0) as client:
                tok_resp = await client.post(GOOGLE_TOKEN_URL, data={
                    "code": code,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                })
                if tok_resp.status_code != 200:
                    logger.error(f"Google token exchange failed: {tok_resp.status_code} {tok_resp.text[:200]}")
                    return RedirectResponse(url="/login?google=error", status_code=303)
                access_token = tok_resp.json().get("access_token")
                if not access_token:
                    return RedirectResponse(url="/login?google=error", status_code=303)
                ui_resp = await client.get(
                    GOOGLE_USERINFO_URL,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                if ui_resp.status_code != 200:
                    logger.error(f"Google userinfo failed: {ui_resp.status_code}")
                    return RedirectResponse(url="/login?google=error", status_code=303)
            gu = ui_resp.json()

            email = (gu.get("email") or "").strip().lower()
            email_verified = bool(gu.get("email_verified", False))
            if not email or not email_verified:
                logger.warning(f"Google OAuth rejected: email missing/unverified ({email or 'none'})")
                return RedirectResponse(url="/login?google=error", status_code=303)

            local = user_store.get_by_email(email)
            if not local:
                try:
                    record = {
                        "email": email,
                        "full_name": gu.get("name") or None,
                        "phone": None,
                        # No password login for OAuth-only accounts; marker hash
                        "password_hash": "oauth_google",
                        "role": "user",
                        "is_active": True,
                        # Consent gate: acceptance captured BEFORE redirecting to
                        # Google (checkbox required on the signup page).
                        "terms_accepted_at": datetime.now(timezone.utc).isoformat(),
                        "terms_version": LEGAL_TERMS_VERSION,
                    }
                    created = supabase_db.insert("users", record) or record
                    local = created if "id" in created else {**record, "id": "google-user"}
                except Exception as e:
                    logger.error(f"Google user creation failed: {e}")
                    return RedirectResponse(url="/login?google=error", status_code=303)

            token = create_session_token(local["id"], local.get("role", "user"), local["email"])
            resp = RedirectResponse(url="/dashboard", status_code=303)
            _set_session_cookie(resp, token)
            return resp
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Google OAuth callback error: {e}")
            return RedirectResponse(url="/login?google=error", status_code=303)

    @app.get("/auth/me", tags=["Auth"])
    async def whoami(request: Request):
        """Returns the current session user info (reads cookie directly: /auth is public)."""
        token = request.cookies.get(SESSION_COOKIE_NAME)
        session = verify_session_token(token) if token else None
        if not session:
            return {"authenticated": False}
        return {
            "authenticated": True,
            "user_id": session.get("sub"),
            "email": session.get("email"),
            "role": session.get("role"),
        }


module_registry.register_module(
    name="auth",
    description="Login/register/logout pages & API, Google direct OAuth, session issuance",
    register_router=register_router,
    # /auth is in legacy PUBLIC_PATH_PREFIXES already; declared here for completeness
    public_prefixes=["/auth"],
    public_exact=["/login", "/register"],
)

"""
Phase 9.7 — per-user connection routes (the three doors).

📘 facebook  : Facebook Login (code flow) → page token + linked-IG discovery
📸 instagram : Instagram child-app Login (instagram_business_*) → IG-only clients
🧵 threads   : existing threads OAuth, now storing per-user

All doors store into platform_connections (encrypted at rest) for the
SESSION user — and service stays gated by entitlements (assert_entitled).
"""
import base64
import hashlib
import hmac as hmac_mod
import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse

from src.config import settings
from src.core.logger import logger
from src.modules.connections.service import connection_service

router = APIRouter()

FB_SCOPES = ("pages_show_list,pages_messaging,pages_manage_metadata,pages_read_engagement,"
             "pages_manage_posts,pages_read_user_content,read_insights,instagram_basic,"
             "instagram_manage_messages,instagram_manage_comments,instagram_content_publish,"
             "pages_utility_messaging")
IG_SCOPES = ("instagram_business_basic,instagram_business_manage_insights,"
             "instagram_business_content_publish,instagram_business_manage_comments,"
             "instagram_business_manage_messages")


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _session(request: Request) -> Optional[dict]:
    from src.core.auth import SESSION_COOKIE_NAME, verify_session_token
    token = request.cookies.get(SESSION_COOKIE_NAME)
    return verify_session_token(token) if token else None


def _require_user(request: Request) -> dict:
    s = _session(request)
    if not s:
        raise HTTPException(status_code=401, detail="authentication required")
    return s


def _sign_state(user_id: str, platform: str) -> str:
    """Stateless CSRF state: payload.user_id.platform.timestamp + HMAC."""
    payload = f"{user_id}.{platform}.{int(time.time())}"
    sig = hmac_mod.new(settings.SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    raw = f"{payload}.{sig}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _verify_state(state: str, platform: str, max_age: int = 900) -> Optional[str]:
    """Returns user_id if valid+fresh, else None (fail-closed).
    Format: b64({user_id}.{platform}.{timestamp}.{hmac})."""
    try:
        raw = base64.urlsafe_b64decode(state.encode()).decode()
        payload, sig = raw.rsplit(".", 1)
        user_id, plat, ts = payload.split(".", 2)
        if plat != platform:
            return None
        if int(time.time()) - int(ts) > max_age:
            return None
        expected = hmac_mod.new(
            settings.SECRET_KEY.encode(), f"{user_id}.{plat}.{ts}".encode(),
            hashlib.sha256).hexdigest()
        if not hmac_mod.compare_digest(sig, expected):
            return None
        return user_id
    except Exception:
        return None


def _redirect_uri(platform: str) -> str:
    return f"{settings.APP_BASE_URL.rstrip('/')}/api/connections/{platform}/callback"


# --------------------------------------------------------------------------
# overview (wizard/settings data: entitlements + connections + upsell)
# --------------------------------------------------------------------------
@router.get("/api/connections", tags=["Connections"])
async def connections_overview(request: Request):
    s = _require_user(request)
    return connection_service.overview(s["sub"])


@router.delete("/api/connections/{platform}", tags=["Connections"])
async def disconnect_platform(platform: str, request: Request):
    s = _require_user(request)
    if platform not in ("facebook", "instagram", "threads"):
        raise HTTPException(status_code=404, detail="unknown platform")
    ok = connection_service.revoke(s["sub"], platform)
    if not ok:
        raise HTTPException(status_code=500, detail="disconnect failed")
    return {"status": "success", "platform": platform, "connected": False}


# --------------------------------------------------------------------------
# 📘 facebook door
# --------------------------------------------------------------------------
@router.get("/api/connections/facebook/authorize", tags=["Connections"])
async def facebook_authorize(request: Request):
    s = _require_user(request)
    # admins operate the workspace (owner) — customers pay the entitlement
    if s.get("role") != "admin" and not connection_service.assert_entitled(s["sub"], "facebook"):
        raise HTTPException(status_code=403, detail="facebook service not in subscription")
    from urllib.parse import urlencode
    params = urlencode({
        "client_id": settings.META_APP_ID,
        "redirect_uri": _redirect_uri("facebook"),
        "scope": FB_SCOPES,
        "response_type": "code",
        "state": _sign_state(s["sub"], "facebook"),
    })
    return {"authorize_url": f"https://www.facebook.com/v26.0/dialog/oauth?{params}"}


@router.get("/api/connections/facebook/callback", tags=["Connections"])
async def facebook_callback(request: Request, code: str = Query(...), state: str = Query(...)):
    user_id = _verify_state(state, "facebook")
    if not user_id:
        return RedirectResponse("/account?connect_error=invalid_state", status_code=303)
    import httpx
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # code → short-lived user token
            tok = await client.get(
                f"{settings.META_GRAPH_API_BASE_URL}/oauth/access_token",
                params={"client_id": settings.META_APP_ID,
                        "client_secret": settings.META_APP_SECRET,
                        "redirect_uri": _redirect_uri("facebook"), "code": code})
            if tok.status_code != 200:
                logger.error(f"FB code exchange failed: {tok.text[:200]}")
                return RedirectResponse("/account?connect_error=facebook", status_code=303)
            short = tok.json().get("access_token")
            # → long-lived user token
            lng = await client.get(
                f"{settings.META_GRAPH_API_BASE_URL}/oauth/access_token",
                params={"grant_type": "fb_exchange_token", "client_id": settings.META_APP_ID,
                        "client_secret": settings.META_APP_SECRET,
                        "fb_exchange_token": short})
            user_token = (lng.json().get("access_token") if lng.status_code == 200 else short) or short
            # → who am I (platform_user_id for deauthorize matching)
            me = await client.get(f"{settings.META_GRAPH_API_BASE_URL}/me",
                                  params={"fields": "id,name", "access_token": user_token})
            me_id = (me.json() if me.status_code == 200 else {}).get("id", "")
            # → pages with linked IG
            pages = await client.get(f"{settings.META_GRAPH_API_BASE_URL}/me/accounts",
                                     params={"fields": "id,name,access_token,"
                                                       "instagram_business_account{id,username}",
                                             "access_token": user_token})
            plist = (pages.json() if pages.status_code == 200 else {}).get("data", [])
            if not plist:
                return RedirectResponse("/account?connect_error=no_pages", status_code=303)
        page = plist[0]
        ig = page.get("instagram_business_account") or {}
        saved = connection_service.store(
            user_id=user_id, platform="facebook",
            access_token=page.get("access_token"),
            account_id=page.get("id"), account_name=page.get("name"),
            scopes=FB_SCOPES.split(","),
            metadata={"platform_user_id": me_id,
                      "linked_ig_id": ig.get("id"),
                      "linked_ig_username": ig.get("username"),
                      "pages_count": len(plist)})
        if not saved:
            return RedirectResponse("/account?connect_error=store", status_code=303)
        return RedirectResponse("/account?connected=facebook", status_code=303)
    except Exception as e:
        logger.error(f"facebook callback error: {e}")
        return RedirectResponse("/account?connect_error=facebook", status_code=303)


# --------------------------------------------------------------------------
# 📸 instagram door (child app — IG-only clients)
# --------------------------------------------------------------------------
@router.get("/api/connections/instagram/authorize", tags=["Connections"])
async def instagram_authorize(request: Request):
    s = _require_user(request)
    if s.get("role") != "admin" and not connection_service.assert_entitled(s["sub"], "instagram"):
        raise HTTPException(status_code=403, detail="instagram service not in subscription")
    if not settings.IG_APP_ID:
        raise HTTPException(status_code=503, detail="Instagram app not configured")
    from urllib.parse import urlencode
    params = urlencode({
        "client_id": settings.IG_APP_ID,
        "redirect_uri": _redirect_uri("instagram"),
        "response_type": "code",
        "scope": IG_SCOPES,
        "state": _sign_state(s["sub"], "instagram"),
    })
    return {"authorize_url": f"https://www.instagram.com/oauth/authorize?{params}"}


@router.get("/api/connections/instagram/callback", tags=["Connections"])
async def instagram_callback(request: Request, code: str = Query(...), state: str = Query(...)):
    user_id = _verify_state(state, "instagram")
    if not user_id:
        return RedirectResponse("/account?connect_error=invalid_state", status_code=303)
    import httpx
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            tok = await client.post("https://api.instagram.com/oauth/access_token", data={
                "client_id": settings.IG_APP_ID, "client_secret": settings.IG_APP_SECRET,
                "grant_type": "authorization_code",
                "redirect_uri": _redirect_uri("instagram"), "code": code})
            if tok.status_code != 200:
                logger.error(f"IG code exchange failed: {tok.text[:200]}")
                return RedirectResponse("/account?connect_error=instagram", status_code=303)
            j = tok.json()
            short, ig_uid = j.get("access_token"), str(j.get("user_id", ""))
            lng = await client.get("https://graph.instagram.com/access_token", params={
                "grant_type": "ig_exchange_token", "client_secret": settings.IG_APP_SECRET,
                "access_token": short})
            token = (lng.json().get("access_token") if lng.status_code == 200 else short) or short
            me = await client.get(f"https://graph.instagram.com/v23.0/{ig_uid}",
                                  params={"fields": "user_id,username", "access_token": token})
            m = me.json() if me.status_code == 200 else {}
        saved = connection_service.store(
            user_id=user_id, platform="instagram", access_token=token,
            account_id=str(m.get("user_id") or ig_uid),
            account_name=f"@{m.get('username')}" if m.get("username") else None,
            scopes=IG_SCOPES.split(","),
            metadata={"platform_user_id": str(ig_uid),
                      "token_expires_in_days": 60})
        if not saved:
            return RedirectResponse("/account?connect_error=store", status_code=303)
        # 60-day token expiry recorded for refresh scheduling
        from datetime import datetime, timedelta, timezone
        from src.core.supabase_client import supabase_db
        try:
            for r in connection_service.list_connections(user_id):
                if r.get("platform") == "instagram" and r.get("account_id") == str(ig_uid):
                    supabase_db.update("platform_connections", r["id"], {
                        "token_expires_at": (datetime.now(timezone.utc)
                                             + timedelta(days=60)).isoformat()})
        except Exception:
            pass
        return RedirectResponse("/account?connected=instagram", status_code=303)
    except Exception as e:
        logger.error(f"instagram callback error: {e}")
        return RedirectResponse("/account?connect_error=instagram", status_code=303)

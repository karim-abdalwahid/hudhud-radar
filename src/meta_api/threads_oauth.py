"""
Threads OAuth & Token Management.

Threads (Meta) uses its OWN app + OAuth flow, separate from the main Meta app.
Flow (official Threads API, graph.threads.net):
1. Authorize: https://threads.net/oauth/authorize?client_id=...&redirect_uri=...&response_type=code&scope=...&state=...
2. Short-lived token:  POST https://graph.threads.net/oauth/access_token (code + client_id + client_secret)
   Returns access_token valid ~1 hour + optional refresh that yields 60-day token.
3. Long-lived:  GET https://graph.threads.net/access_token?grant_type=th_exchange_token&client_secret=...&access_token=<short>
   Returns 60-day token.
4. Refresh:  GET https://graph.threads.net/refresh_access_token?grant_type=th_refresh_token&access_token=<long>

Tokens are persisted in Supabase app_settings['threads_credentials'] (serverless-safe)
with expiry tracking. The publisher consumes them from there.
"""
import secrets
import time
from typing import Any, Dict, Optional
from urllib.parse import quote, urlencode

import httpx

from src.config import settings
from src.core.logger import logger
from src.core.supabase_client import supabase_db

# Official Threads scopes for publishing + reading replies
THREADS_SCOPES = (
    "threads_basic,threads_content_publish,threads_manage_replies,"
    "threads_manage_insights,threads_read_replies"
)

THREADS_AUTH_URL = "https://threads.net/oauth/authorize"
THREADS_GRAPH_BASE = "https://graph.threads.net"


def _get_stored_creds() -> Dict[str, Any]:
    try:
        return supabase_db.get_setting("threads_credentials") or {}
    except Exception:
        return {}


def _save_stored_creds(creds: Dict[str, Any]) -> bool:
    try:
        return supabase_db.set_setting("threads_credentials", creds)
    except Exception as e:
        logger.warning(f"Failed to persist threads credentials: {e}")
        return False


class ThreadsOAuthManager:
    """Manages the Threads app OAuth lifecycle and token storage."""

    def __init__(self):
        self._pending_states: Dict[str, float] = {}  # state -> created_at (CSRF, 10 min TTL)

    # ------------------------------------------------------------------
    # Step 1: build the authorize URL
    # ------------------------------------------------------------------
    def build_authorize_url(self) -> Dict[str, Any]:
        app_id = settings.THREADS_APP_ID
        if not app_id:
            return {"status": "error", "detail": "THREADS_APP_ID غير مضبوط"}
        state = secrets.token_urlsafe(24)
        self._pending_states[state] = time.time()
        # Prune stale states (>10 minutes)
        now = time.time()
        self._pending_states = {s: t for s, t in self._pending_states.items() if now - t < 600}

        params = {
            "client_id": app_id,
            "redirect_uri": settings.THREADS_REDIRECT_URI,
            "response_type": "code",
            "scope": THREADS_SCOPES,
            "state": state,
        }
        url = f"{THREADS_AUTH_URL}?{urlencode(params, quote_via=quote)}"
        return {"status": "success", "authorize_url": url, "state": state}

    def validate_state(self, state: Optional[str]) -> bool:
        """Validates and consumes a pending OAuth state (CSRF guard)."""
        if not state or state not in self._pending_states:
            return False
        created = self._pending_states.pop(state)
        return (time.time() - created) < 600

    # ------------------------------------------------------------------
    # Step 2+3: exchange code -> short token -> long-lived token
    # ------------------------------------------------------------------
    async def exchange_code(self, code: str) -> Dict[str, Any]:
        app_id = settings.THREADS_APP_ID
        app_secret = settings.THREADS_APP_SECRET
        if not app_id or not app_secret:
            return {"status": "error", "detail": "THREADS_APP_ID/SECRET غير مضبوطين"}

        async with httpx.AsyncClient(timeout=20.0) as client:
            # Short-lived token
            short = await client.post(
                f"{THREADS_GRAPH_BASE}/oauth/access_token",
                data={
                    "client_id": app_id,
                    "client_secret": app_secret,
                    "grant_type": "authorization_code",
                    "redirect_uri": settings.THREADS_REDIRECT_URI,
                    "code": code,
                },
            )
            if short.status_code != 200:
                return {"status": "error", "detail": f"Token exchange failed: {short.text[:300]}"}
            short_data = short.json()
            short_token = short_data.get("access_token")

            # Long-lived 60-day token
            long_resp = await client.get(
                f"{THREADS_GRAPH_BASE}/access_token",
                params={
                    "grant_type": "th_exchange_token",
                    "client_secret": app_secret,
                    "access_token": short_token,
                },
            )
            if long_resp.status_code != 200:
                # Fall back to the short token if exchange fails
                logger.warning(f"Threads long-token exchange failed: {long_resp.text[:200]}")
                return await self._finalize_credentials(short_token, expires_in=short_data.get("expires_in", 3600))

            long_data = long_resp.json()
            return await self._finalize_credentials(
                long_data.get("access_token"),
                expires_in=long_data.get("expires_in", 5184000),
            )

    async def _finalize_credentials(self, token: str, expires_in: int) -> Dict[str, Any]:
        """Fetches the Threads profile and persists credentials."""
        profile: Dict[str, Any] = {}
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                me = await client.get(
                    f"{THREADS_GRAPH_BASE}/me",
                    params={"fields": "id,username,threads_profile_picture_url", "access_token": token},
                )
                if me.status_code == 200:
                    profile = me.json()
        except Exception as e:
            logger.warning(f"Threads profile fetch failed: {e}")

        creds = {
            "access_token": token,
            "expires_at": int(time.time() + expires_in),
            "expires_in": expires_in,
            "connected_at": int(time.time()),
            "threads_user_id": profile.get("id"),
            "threads_username": profile.get("username"),
        }
        saved = _save_stored_creds(creds)
        logger.info(f"Threads connected: @{profile.get('username')} (persisted={saved})")
        return {
            "status": "success",
            "username": profile.get("username"),
            "threads_user_id": profile.get("id"),
            "expires_in_days": round(expires_in / 86400, 1),
            "persisted": saved,
        }

    # ------------------------------------------------------------------
    # Refresh (60-day tokens are refreshable while valid)
    # ------------------------------------------------------------------
    async def refresh_token(self) -> Dict[str, Any]:
        creds = _get_stored_creds()
        token = creds.get("access_token")
        if not token:
            return {"status": "error", "detail": "لا يوجد توكن Threads محفوظ"}
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                f"{THREADS_GRAPH_BASE}/refresh_access_token",
                params={"grant_type": "th_refresh_token", "access_token": token},
            )
        if resp.status_code != 200:
            return {"status": "error", "detail": f"Refresh failed: {resp.text[:200]}"}
        data = resp.json()
        creds["access_token"] = data.get("access_token")
        creds["expires_in"] = data.get("expires_in", 5184000)
        creds["expires_at"] = int(time.time() + creds["expires_in"])
        creds["refreshed_at"] = int(time.time())
        _save_stored_creds(creds)
        return {"status": "success", "expires_in_days": round(creds["expires_in"] / 86400, 1)}

    # ------------------------------------------------------------------
    # Status & disconnect
    # ------------------------------------------------------------------
    def get_status(self) -> Dict[str, Any]:
        creds = _get_stored_creds()
        token = creds.get("access_token")
        configured = bool(settings.THREADS_APP_ID and settings.THREADS_APP_SECRET)
        if not token:
            return {"configured": configured, "connected": False}
        return {
            "configured": configured,
            "connected": True,
            "username": creds.get("threads_username"),
            "threads_user_id": creds.get("threads_user_id"),
            "expires_at": creds.get("expires_at"),
            "expires_in_days": round(max(0, (creds.get("expires_at", 0) - time.time())) / 86400, 1),
        }

    def disconnect(self) -> Dict[str, Any]:
        removed = _save_stored_creds({})
        return {"status": "success", "disconnected": True, "persisted": removed}


# ------------------------------------------------------------------
# Token accessor for the publisher (live credentials with freshness check)
# ------------------------------------------------------------------
def get_active_threads_token() -> Optional[str]:
    """Returns a valid Threads token or None (checks expiry)."""
    creds = _get_stored_creds()
    token = creds.get("access_token")
    if not token:
        return None
    if creds.get("expires_at", 0) < time.time() + 300:  # 5-minute safety buffer
        return None
    return token


threads_oauth = ThreadsOAuthManager()

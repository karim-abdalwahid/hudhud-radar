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
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from urllib.parse import quote, urlencode

import httpx

from src.config import settings
from src.core.logger import logger
from src.core.supabase_client import supabase_db

# Official Threads scopes for publishing + reading replies + content lifecycle
THREADS_SCOPES = (
    "threads_basic,threads_content_publish,threads_manage_replies,"
    "threads_manage_insights,threads_read_replies,threads_delete"
)

THREADS_AUTH_URL = "https://threads.net/oauth/authorize"
THREADS_GRAPH_BASE = "https://graph.threads.net"


def _get_stored_creds() -> Dict[str, Any]:
    try:
        stored = supabase_db.get_setting("threads_credentials") or {}
        if stored.get("access_token"):
            return stored
    except Exception:
        pass
    # Legacy env fallback (.env THREADS_ACCESS_TOKEN) — used until the owner
    # connects via the official OAuth flow. Expires_at=0 means never-expiring.
    if settings.THREADS_ACCESS_TOKEN:
        return {
            "access_token": settings.THREADS_ACCESS_TOKEN,
            "expires_at": 0,
            "user_id": settings.THREADS_USER_ID,
            "source": "env_fallback",
        }
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
    # CSRF state store — persisted to Supabase app_settings so the OAuth
    # callback can hit a DIFFERENT serverless instance than /authorize
    # (in-memory dict caused random "state not found" failures on Vercel).
    # Memory dict remains as fast-path/fallback mirror.
    # ------------------------------------------------------------------
    def _persist_state(self, state: str, created_at: float):
        """Persists the CSRF state to app_settings — serverless-safe (the
        authorize request and the callback may hit different instances)."""
        self._pending_states[state] = created_at
        try:
            payload = supabase_db.get_setting("threads_oauth_states") or {}
            states = payload.get("states", {}) if isinstance(payload, dict) else {}
            now = time.time()
            states = {s: ts for s, ts in states.items() if now - float(ts) <= 600}
            states[state] = created_at
            supabase_db.set_setting("threads_oauth_states", {"states": states})
        except Exception as e:
            logger.warning(f"OAuth state DB persist failed (memory fallback): {e}")
        try:
            payload = {"states": {state: created_at}, "updated_at": datetime.now(timezone.utc).isoformat()}
            supabase_db.set_setting("threads_oauth_states", payload)
        except Exception as e:
            logger.warning(f"Could not persist OAuth state to Supabase (memory-only): {e}")

    def _load_stored_state(self, state: str) -> Optional[float]:
        try:
            payload = supabase_db.get_setting("threads_oauth_states") or {}
            stored = payload.get("states", {}) if isinstance(payload, dict) else {}
            if state in stored:
                return float(stored[state])
        except Exception:
            pass
        return None

    # ------------------------------------------------------------------
    # Step 1: build the authorize URL
    # ------------------------------------------------------------------
    def build_authorize_url(self) -> Dict[str, Any]:
        app_id = settings.THREADS_APP_ID
        if not app_id:
            return {"status": "error", "detail": "THREADS_APP_ID غير مضبوط"}
        state = secrets.token_urlsafe(24)
        # Prune stale states (>10 minutes)
        now = time.time()
        self._pending_states = {s: t for s, t in self._pending_states.items() if now - t < 600}
        self._persist_state(state, now)

        params = {
            "client_id": app_id,
            "redirect_uri": settings.EFFECTIVE_THREADS_REDIRECT_URI,
            "response_type": "code",
            "scope": THREADS_SCOPES,
            "state": state,
        }
        url = f"{THREADS_AUTH_URL}?{urlencode(params, quote_via=quote)}"
        return {"status": "success", "authorize_url": url, "state": state}

    def validate_state(self, state: Optional[str]) -> bool:
        """Validates and consumes a pending OAuth state (CSRF guard).
        Checks memory first, then the Supabase-persisted store (cross-instance)."""
        if not state:
            return False
        created = self._pending_states.pop(state, None)
        if created is None:
            created = self._load_stored_state(state)
            if created is not None:
                try:
                    supabase_db.set_setting("threads_oauth_states", {"states": {}, "updated_at": datetime.now(timezone.utc).isoformat()})
                except Exception:
                    pass
        if created is None:
            return False
        return (time.time() - created) < 600

    # ------------------------------------------------------------------
    # Step 2+3: exchange code -> short token -> long-lived token
    # ------------------------------------------------------------------
    async def exchange_code(self, code: str, user_id: Optional[str] = None) -> Dict[str, Any]:
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
                    "redirect_uri": settings.EFFECTIVE_THREADS_REDIRECT_URI,
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
                return await self._finalize_credentials(short_token,
                                                        expires_in=short_data.get("expires_in", 3600),
                                                        user_id=user_id)

            long_data = long_resp.json()
            return await self._finalize_credentials(
                long_data.get("access_token"),
                expires_in=long_data.get("expires_in", 5184000),
                user_id=user_id,
            )

    async def _finalize_credentials(self, token: str, expires_in: int,
                                    user_id: Optional[str] = None) -> Dict[str, Any]:
        """Fetches the Threads profile and persists credentials.
        user_id given → per-user connection (platform_connections, encrypted);
        user_id None  → legacy global app_settings (admin/compat path)."""
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

        if user_id:
            from src.modules.connections.service import connection_service
            from datetime import datetime, timedelta, timezone
            expires_at = (datetime.now(timezone.utc)
                          + timedelta(seconds=expires_in)).isoformat()
            saved = connection_service.store(
                user_id=user_id, platform="threads", access_token=token,
                account_id=str(profile.get("id") or ""),
                account_name=f"@{profile.get('username')}" if profile.get("username") else None,
                scopes=[s for s in THREADS_SCOPES.split(",") if s],
                token_expires_at=expires_at,
                metadata={"platform_user_id": str(profile.get("id") or "")})
            logger.info(f"Threads connected (per-user): user={user_id} "
                        f"@{profile.get('username')} (persisted={bool(saved)})")
            return {
                "status": "success",
                "username": profile.get("username"),
                "threads_user_id": profile.get("id"),
                "expires_in_days": round(expires_in / 86400, 1),
                "persisted": bool(saved),
                "per_user": True,
            }

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
    # Proactive refresh (Wave 9.8 cron): refresh any Threads token — legacy
    # global or per-user connections — expiring within 7 days.
    # ------------------------------------------------------------------
    async def refresh_if_expiring(self, days_threshold: int = 7) -> Dict[str, Any]:
        from datetime import datetime, timedelta
        refreshed, failed = [], []
        cutoff = time.time() + days_threshold * 86400

        # 1) Legacy global token
        creds = _get_stored_creds()
        exp = creds.get("expires_at") or 0
        if creds.get("access_token") and exp and exp < cutoff:
            res = await self.refresh_token()
            (refreshed if res.get("status") == "success" else failed).append("legacy")

        # 2) Per-user platform_connections (threads)
        try:
            rows = supabase_db.select("platform_connections",
                                      {"platform": "threads", "status": "active"}) or []
        except Exception:
            rows = []
        for r in rows:
            exp_s = r.get("token_expires_at")
            try:
                exp_dt = datetime.fromisoformat(str(exp_s).replace("Z", "+00:00")) if exp_s else None
            except Exception:
                exp_dt = None
            if not exp_dt or exp_dt.timestamp() >= cutoff:
                continue
            try:
                from src.core.crypto import decrypt_token, encrypt_token
                tok = decrypt_token(r.get("access_token_encrypted") or "")
                if not tok:
                    continue
                async with httpx.AsyncClient(timeout=20.0) as client:
                    resp = await client.get(
                        f"{THREADS_GRAPH_BASE}/refresh_access_token",
                        params={"grant_type": "th_refresh_token", "access_token": tok},
                    )
                if resp.status_code != 200:
                    failed.append(str(r.get("user_id"))[:8])
                    logger.warning(f"Threads per-user refresh failed for {str(r.get('user_id'))[:8]}: {resp.status_code}")
                    continue
                data = resp.json()
                new_exp = datetime.now(timezone.utc) + timedelta(
                    seconds=int(data.get("expires_in", 5184000)))
                updates = {
                    "access_token_encrypted": encrypt_token(data.get("access_token")),
                    "token_expires_at": new_exp.isoformat(),
                }
                if data.get("refresh_token"):
                    md = dict(r.get("metadata") or {})
                    md["refresh_token_encrypted"] = encrypt_token(data["refresh_token"])
                    updates["metadata"] = md
                supabase_db.update("platform_connections", r["id"], updates)
                refreshed.append(str(r.get("user_id"))[:8])
                logger.info(f"Threads per-user token refreshed for {str(r.get('user_id'))[:8]}")
            except Exception as e:
                failed.append(str(r.get("user_id"))[:8])
                logger.warning(f"Threads per-user refresh error for {str(r.get('user_id'))[:8]}: {e}")

        return {"status": "success", "refreshed": refreshed, "failed": failed}

    # ------------------------------------------------------------------
    # Status & disconnect
    # ------------------------------------------------------------------
    def get_status(self) -> Dict[str, Any]:
        creds = _get_stored_creds()
        token = creds.get("access_token")
        configured = bool(settings.THREADS_APP_ID and settings.THREADS_APP_SECRET)
        if not token:
            return {"configured": configured, "connected": False}
        status = {
            "configured": configured,
            "connected": True,
            "username": creds.get("threads_username"),
            "threads_user_id": creds.get("threads_user_id"),
            "expires_at": creds.get("expires_at"),
            "expires_in_days": round(max(0, (creds.get("expires_at", 0) - time.time())) / 86400, 1),
        }
        # Enrich from the real per-user connection when the legacy env token
        # carries no identity/expiry (settings page shows the truth, same UI).
        if not status["username"] or not status.get("expires_at"):
            try:
                rows = supabase_db.select("platform_connections",
                                          {"platform": "threads", "status": "active"}) or []
                if rows:
                    rows.sort(key=lambda r: r.get("updated_at") or r.get("connected_at") or "", reverse=True)
                    conn = rows[0]
                    if not status["username"]:
                        status["username"] = (conn.get("account_name") or "").lstrip("@") or None
                    if not status["threads_user_id"]:
                        status["threads_user_id"] = conn.get("account_id") or None
                    exp_s = conn.get("token_expires_at")
                    if exp_s and not status.get("expires_at"):
                        try:
                            from datetime import datetime as _dt
                            exp_dt = _dt.fromisoformat(str(exp_s).replace("Z", "+00:00"))
                            status["expires_at"] = int(exp_dt.timestamp())
                            status["expires_in_days"] = round(
                                max(0, exp_dt.timestamp() - time.time()) / 86400, 1)
                        except Exception:
                            pass
                    status["source"] = "per_user_connection"
            except Exception as e:
                logger.debug(f"Threads status enrichment skipped: {e}")
        return status

    def disconnect(self) -> Dict[str, Any]:
        removed = _save_stored_creds({})
        return {"status": "success", "disconnected": True, "persisted": removed}


# ------------------------------------------------------------------
# Token accessor for the publisher (live credentials with freshness check)
# ------------------------------------------------------------------
def get_active_threads_token() -> Optional[str]:
    """Returns a valid Threads token or None (checks expiry).
    Resolution order: per-user platform_connections (first active) → legacy
    global app_settings (compat shim — removed at Wave 9.8 cutover)."""
    try:
        from datetime import datetime, timedelta, timezone
        from src.core.crypto import decrypt_token
        rows = supabase_db.select("platform_connections",
                                  {"platform": "threads", "status": "active"}) or []
        for r in rows:
            exp = r.get("token_expires_at")
            if exp:
                try:
                    if datetime.fromisoformat(str(exp).replace("Z", "+00:00")) \
                            <= datetime.now(timezone.utc) + timedelta(seconds=300):
                        continue  # expired / expiring within the 5-min buffer
                except Exception:
                    pass
            try:
                return decrypt_token(r.get("access_token_encrypted") or "")
            except Exception:
                continue
    except Exception:
        pass
    creds = _get_stored_creds()
    token = creds.get("access_token")
    if not token:
        return None
    expires_at = creds.get("expires_at") or 0
    if expires_at and expires_at < time.time() + 300:  # 5-minute safety buffer (0 = never expires)
        return None
    return token




threads_oauth = ThreadsOAuthManager()

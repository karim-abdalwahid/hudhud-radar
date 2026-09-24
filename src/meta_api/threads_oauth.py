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

Each customer's token is stored encrypted in its own ``platform_connections``
row.  The OAuth application configuration itself remains in the environment.
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
    """Compatibility shim: global Threads credentials are intentionally gone."""
    return {}


def _save_stored_creds(creds: Dict[str, Any]) -> bool:
    """Compatibility shim that refuses global credential storage."""
    return False


class ThreadsOAuthManager:
    """Manages the Threads app OAuth lifecycle and token storage."""

    def __init__(self):
        # state -> {created_at, user_id}; binding a state to the initiating
        # workspace prevents account A's callback from being completed in B.
        self._pending_states: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # CSRF state store — persisted to Supabase app_settings so the OAuth
    # callback can hit a DIFFERENT serverless instance than /authorize
    # (in-memory dict caused random "state not found" failures on Vercel).
    # Memory dict remains as fast-path/fallback mirror.
    # ------------------------------------------------------------------
    def _persist_state(self, state: str, created_at: float, user_id: str):
        """Persists the CSRF state to app_settings — serverless-safe (the
        authorize request and the callback may hit different instances)."""
        self._pending_states[state] = {"created_at": created_at, "user_id": user_id}
        try:
            payload = supabase_db.get_setting("threads_oauth_states") or {}
            states = payload.get("states", {}) if isinstance(payload, dict) else {}
            now = time.time()
            states = {
                s: value for s, value in states.items()
                if isinstance(value, dict) and value.get("user_id")
                and now - float(value.get("created_at", 0)) <= 600
            }
            states[state] = {"created_at": created_at, "user_id": user_id}
            supabase_db.set_setting("threads_oauth_states", {"states": states})
        except Exception as e:
            logger.warning(f"OAuth state DB persist failed (memory fallback): {e}")

    def _load_stored_state(self, state: str) -> Optional[Dict[str, Any]]:
        try:
            payload = supabase_db.get_setting("threads_oauth_states") or {}
            stored = payload.get("states", {}) if isinstance(payload, dict) else {}
            if state in stored:
                value = stored[state]
                # States written by older builds had no owner.  They must not
                # be accepted because a different signed-in customer could
                # finish the OAuth flow with them.
                if isinstance(value, dict) and value.get("user_id"):
                    return {"created_at": float(value.get("created_at", 0)),
                            "user_id": str(value["user_id"])}
        except Exception:
            pass
        return None

    # ------------------------------------------------------------------
    # Step 1: build the authorize URL
    # ------------------------------------------------------------------
    def build_authorize_url(self, user_id: str) -> Dict[str, Any]:
        app_id = settings.THREADS_APP_ID
        if not app_id:
            return {"status": "error", "detail": "THREADS_APP_ID غير مضبوط"}
        state = secrets.token_urlsafe(24)
        # Prune stale states (>10 minutes)
        now = time.time()
        self._pending_states = {
            s: value for s, value in self._pending_states.items()
            if now - float(value.get("created_at", 0)) < 600
        }
        self._persist_state(state, now, user_id)

        params = {
            "client_id": app_id,
            "redirect_uri": settings.EFFECTIVE_THREADS_REDIRECT_URI,
            "response_type": "code",
            "scope": THREADS_SCOPES,
            "state": state,
        }
        url = f"{THREADS_AUTH_URL}?{urlencode(params, quote_via=quote)}"
        return {"status": "success", "authorize_url": url, "state": state}

    def validate_state(self, state: Optional[str], user_id: str) -> bool:
        """Validates and consumes a pending OAuth state (CSRF guard).
        Checks memory first, then the Supabase-persisted store (cross-instance)."""
        if not state:
            return False
        pending = self._pending_states.pop(state, None)
        created = pending.get("created_at") if pending else None
        state_owner = str(pending.get("user_id")) if pending else None
        if created is None:
            saved = self._load_stored_state(state)
            if saved is not None:
                created = saved["created_at"]
                state_owner = saved["user_id"]
                try:
                    payload = supabase_db.get_setting("threads_oauth_states") or {}
                    states = payload.get("states", {}) if isinstance(payload, dict) else {}
                    states.pop(state, None)
                    supabase_db.set_setting("threads_oauth_states", {"states": states,
                        "updated_at": datetime.now(timezone.utc).isoformat()})
                except Exception:
                    pass
        if created is None or state_owner != str(user_id):
            return False
        return (time.time() - created) < 600

    # ------------------------------------------------------------------
    # Step 2+3: exchange code -> short token -> long-lived token
    # ------------------------------------------------------------------
    async def exchange_code(self, code: str, user_id: str) -> Dict[str, Any]:
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
                                    user_id: str) -> Dict[str, Any]:
        """Fetches the Threads profile and persists credentials.
        Credentials are always written to the tenant's encrypted connection."""
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

    # ------------------------------------------------------------------
    # Refresh (60-day tokens are refreshable while valid)
    # ------------------------------------------------------------------
    async def refresh_token(self, user_id: str) -> Dict[str, Any]:
        from src.modules.connections.service import connection_service
        token = connection_service.get_active_token(user_id, "threads")
        if not token:
            return {"status": "error", "detail": "لا يوجد اتصال Threads مفعّل لهذا الحساب"}
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                f"{THREADS_GRAPH_BASE}/refresh_access_token",
                params={"grant_type": "th_refresh_token", "access_token": token},
            )
        if resp.status_code != 200:
            return {"status": "error", "detail": f"Refresh failed: {resp.text[:200]}"}
        data = resp.json()
        expires_in = int(data.get("expires_in", 5184000))
        rows = supabase_db.select("platform_connections", {
            "user_id": user_id, "platform": "threads", "status": "active"}) or []
        if len(rows) != 1:
            return {"status": "error", "detail": "تعذر تحديد اتصال Threads واحد لهذا الحساب"}
        from src.core.crypto import encrypt_token
        from datetime import timedelta
        supabase_db.update("platform_connections", rows[0]["id"], {
            "access_token_encrypted": encrypt_token(data.get("access_token") or token),
            "token_expires_at": (datetime.now(timezone.utc) + timedelta(seconds=expires_in)).isoformat(),
        })
        return {"status": "success", "expires_in_days": round(expires_in / 86400, 1)}

    # ------------------------------------------------------------------
    # Proactive refresh for encrypted per-user connections expiring within 7 days.
    # ------------------------------------------------------------------
    async def refresh_if_expiring(self, days_threshold: int = 7) -> Dict[str, Any]:
        from datetime import datetime, timedelta
        refreshed, failed = [], []
        cutoff = time.time() + days_threshold * 86400

        # Per-user platform_connections (threads)
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
    def get_status(self, user_id: str) -> Dict[str, Any]:
        """Return only the signed-in customer's connection status."""
        configured = bool(settings.THREADS_APP_ID and settings.THREADS_APP_SECRET)
        try:
            rows = supabase_db.select("platform_connections", {
                "user_id": user_id, "platform": "threads", "status": "active"}) or []
        except Exception:
            rows = []
        if len(rows) != 1:
            return {"status": "success", "configured": configured, "connected": False}
        conn = rows[0]
        exp_s = conn.get("token_expires_at")
        expires_at = None
        if exp_s:
            try:
                expires_at = int(datetime.fromisoformat(str(exp_s).replace("Z", "+00:00")).timestamp())
            except Exception:
                pass
        status = {
            "status": "success",
            "configured": configured,
            "connected": True,
            "username": (conn.get("account_name") or "").lstrip("@") or None,
            "threads_user_id": conn.get("account_id") or None,
            "expires_at": expires_at,
            "expires_in_days": round(max(0, (expires_at or 0) - time.time()) / 86400, 1) if expires_at else None,
            "source": "per_user_connection",
        }
        return status

    def disconnect(self, user_id: str) -> Dict[str, Any]:
        from src.modules.connections.service import connection_service
        removed = connection_service.revoke(user_id, "threads")
        return {"status": "success" if removed else "error", "disconnected": bool(removed)}


# ------------------------------------------------------------------
# Token accessor for the publisher (live credentials with freshness check)
# ------------------------------------------------------------------
def get_active_threads_token(user_id: str) -> Optional[str]:
    """Backward-compatible accessor that remains tenant-bound."""
    from src.modules.connections.service import connection_service
    return connection_service.get_active_token(user_id, "threads")




threads_oauth = ThreadsOAuthManager()

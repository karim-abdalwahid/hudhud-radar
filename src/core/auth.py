"""
Authentication & Session Management for HudhudRadar.

Security model:
- Passwords hashed with PBKDF2-HMAC-SHA256 (stdlib, 390k iterations, per-user salt).
- Sessions via HMAC-signed cookies (SECRET_KEY), stateless but server-verifiable.
- First registered user becomes 'admin' (owner). Subsequent users require an
  invite/registration flag until SaaS phase.
- Route protection enforced by AuthMiddleware on all dashboard/API routes.
Public routes: landing, auth pages/actions, health, webhooks, static assets, docs.
"""
import base64
import hashlib
import hmac
import json
import os
import secrets
import time
import uuid
from typing import Any, Dict, Optional

from src.config import settings
from src.core.logger import logger

SESSION_COOKIE_NAME = "hudhud_session"
SESSION_TTL_SECONDS = 60 * 60 * 24 * 7  # 7 days
PBKDF2_ITERATIONS = 390_000

# Exact public paths (no session required)
PUBLIC_EXACT_PATHS = frozenset({
    "/",            # landing page
    "/login",
    "/register",
    "/privacy",
    "/data-deletion",
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/favicon.ico",
})

# Public path prefixes (no session required)
PUBLIC_PATH_PREFIXES = (
    "/static",
    "/webhooks",
    "/api/webhook",
    "/auth",        # auth API endpoints (login/register/logout)
    "/api/cron",    # cron endpoints (protected by their own CRON_SECRET check)
    "/api/data-deletion",    # Meta data-deletion callback (HMAC-verified, sessionless by design)
    "/api/threads/uninstall",  # Threads uninstall callback (HMAC-verified, sessionless by design)
    "/favicon",
)

# Admin-only API endpoints (any method)
ADMIN_EXACT_PATHS = frozenset({
    "/api/meta/configure",
    "/api/meta/exchange-token",
    "/api/meta/user-pages",
    "/api/meta/subscribe-page",
    "/api/meta/sync-posts",
    "/api/onboarding/save-all",
    "/api/content/scheduler/trigger",
    "/api/threads/oauth/authorize",
    "/api/threads/oauth/refresh",
    "/api/threads/disconnect",
})

# Admin-only dashboard pages (server-side enforcement of Developer Console)
ADMIN_PAGE_PATHS = frozenset({
    "/settings",
    "/identity",
    "/analytics",
})

# Admin-only API path prefixes (any method)
ADMIN_PATH_PREFIXES = (
    "/api/identity",
    "/api/ai/providers",
    "/api/ai/models",
)

# Admin-only mutations on these prefixes (GET allowed for logged-in users)
ADMIN_MUTATION_PREFIXES = (
    "/api/knowledge",
    "/api/automations",
    "/api/content",
)


# --------------------------------------------------------------------
# Password Hashing (PBKDF2-HMAC-SHA256)
# --------------------------------------------------------------------
def hash_password(password: str) -> str:
    """Returns 'pbkdf2_sha256$iterations$salt_hex$hash_hex'."""
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Constant-time password verification against stored hash string."""
    try:
        algo, iterations, salt_hex, hash_hex = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)
        )
        return hmac.compare_digest(dk.hex(), hash_hex)
    except Exception:
        return False


# --------------------------------------------------------------------
# Stateless signed session token: base64(payload).base64(hmac)
# --------------------------------------------------------------------
def _sign(data: bytes) -> str:
    mac = hmac.new(settings.SECRET_KEY.encode("utf-8"), data, hashlib.sha256)
    return base64.urlsafe_b64encode(mac.digest()).decode("ascii")


def create_session_token(user_id: str, role: str, email: str) -> str:
    payload = json.dumps(
        {
            "sub": user_id,
            "role": role,
            "email": email,
            "iat": int(time.time()),
            "exp": int(time.time()) + SESSION_TTL_SECONDS,
            "jti": uuid.uuid4().hex,
        },
        separators=(",", ":"),
    )
    raw = base64.urlsafe_b64encode(payload.encode("utf-8"))
    return f"{raw.decode('ascii')}.{_sign(raw)}"


def verify_session_token(token: str) -> Optional[Dict[str, Any]]:
    """Returns session payload dict or None if invalid/expired."""
    try:
        raw_b64, sig = token.rsplit(".", 1)
        raw = raw_b64.encode("ascii")
        if not hmac.compare_digest(_sign(raw), sig):
            return None
        payload = json.loads(base64.urlsafe_b64decode(raw))
        if int(payload.get("exp", 0)) < time.time():
            return None
        return payload
    except Exception:
        return None


# --------------------------------------------------------------------
# User Store (Supabase primary, in-memory fallback for local dev)
# --------------------------------------------------------------------
class UserStore:
    """CRUD over Supabase `users` table with in-memory dev fallback."""

    def __init__(self):
        self._memory_users: Dict[str, Dict[str, Any]] = {}

    def _memory_fallback(self) -> bool:
        from src.core.supabase_client import supabase_db
        return not supabase_db.is_connected

    def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        email = (email or "").strip().lower()
        from src.core.supabase_client import supabase_db
        if not self._memory_fallback():
            try:
                rows = supabase_db.select("users", {"email": email}) or []
                return rows[0] if rows else None
            except Exception as e:
                logger.warning(f"user lookup failed, memory fallback: {e}")
        for u in self._memory_users.values():
            if u["email"] == email:
                return u
        return None

    def get_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        from src.core.supabase_client import supabase_db
        if not self._memory_fallback():
            try:
                rows = supabase_db.select("users", {"id": user_id}) or []
                return rows[0] if rows else None
            except Exception as e:
                logger.warning(f"user lookup failed, memory fallback: {e}")
        return self._memory_users.get(user_id)

    def count(self) -> int:
        from src.core.supabase_client import supabase_db
        if not self._memory_fallback():
            try:
                rows = supabase_db.select("users") or []
                return len(rows)
            except Exception as e:
                logger.warning(f"user count failed, memory fallback: {e}")
        return len(self._memory_users)

    def create_user(
        self, email: str, password: str, phone: Optional[str] = None, full_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Creates a user. First-ever user is promoted to admin (owner)."""
        email = (email or "").strip().lower()
        if self.get_by_email(email):
            raise ValueError("البريد الإلكتروني مسجل بالفعل")
        role = "admin" if self.count() == 0 else "user"
        record = {
            "email": email,
            "phone": (phone or "").strip() or None,
            "full_name": (full_name or "").strip() or None,
            "password_hash": hash_password(password),
            "role": role,
            "is_active": True,
        }
        from src.core.supabase_client import supabase_db

        # In-memory mode (dev/test isolation): never touch the cloud DB
        if self._memory_fallback():
            record = {**record, "id": str(uuid.uuid4())}
            self._memory_users[record["id"]] = record
            logger.info(f"New user registered (memory store): {email} (role={role})")
            return record

        try:
            created = supabase_db.insert("users", record)
        except Exception as e:
            logger.error(f"User insert failed: {e}")
            raise ValueError(
                "تعذر إنشاء الحساب — تأكد من تنفيذ ترحيل قاعدة البيانات "
                "(database/migrations/001_users_auth_and_security.sql) في Supabase SQL Editor أولاً"
            )
        created = created or {**record, "id": str(uuid.uuid4())}
        logger.info(f"New user registered: {email} (role={created.get('role')})")
        return created

    def authenticate(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        user = self.get_by_email(email)
        if not user or not user.get("is_active", False):
            return None
        if not verify_password(password, user.get("password_hash", "")):
            return None
        from src.core.supabase_client import supabase_db
        try:
            supabase_db.update("users", user["id"], {"last_login_at": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime())})
        except Exception:
            pass
        return user


user_store = UserStore()


# --------------------------------------------------------------------
# Rate limiting for auth endpoints (brute-force protection)
# --------------------------------------------------------------------
class AuthAttemptLimiter:
    """Simple in-memory sliding window: max 10 attempts / 5 minutes per IP."""

    def __init__(self, max_attempts: int = 10, window_seconds: int = 300):
        self.max_attempts = max_attempts
        self.window = window_seconds
        self._history: Dict[str, list] = {}

    def is_blocked(self, key: str) -> bool:
        now = time.time()
        attempts = [t for t in self._history.get(key, []) if now - t < self.window]
        self._history[key] = attempts
        return len(attempts) >= self.max_attempts

    def record(self, key: str):
        self._history.setdefault(key, []).append(time.time())


auth_limiter = AuthAttemptLimiter()

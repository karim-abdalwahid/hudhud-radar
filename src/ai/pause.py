"""
AI Pause (Wave 9.8 — owner request): a per-user master switch that silences
the autonomous AI across ALL conversations, replies, and comment automations,
so the user can manage their pages personally.

Semantics:
- Human Takeover stays per-conversation and unchanged.
- The GLOBAL pause (this switch) overrides everything: when ON, the AI never
  auto-replies anywhere for that user — messages are still stored so a human
  can answer manually from the inbox.

Storage:
- users.ai_paused (migration 018) — the user's own switch.
- app_settings.ai_autonomous_paused — the legacy/global operator switch
  (single-tenant reality: the legacy env-token operation has no per-lead owner).
"""
from typing import Any, Dict, Optional

from src.core.logger import logger
from src.core.supabase_client import supabase_db

GLOBAL_PAUSE_KEY = "ai_autonomous_paused"


def _global_paused() -> bool:
    try:
        return bool(supabase_db.get_setting(GLOBAL_PAUSE_KEY))
    except Exception as e:
        logger.warning(f"Global AI pause check failed (non-blocking): {e}")
        return False


def _user_paused(user_id: str) -> bool:
    try:
        rows = supabase_db.select("users", {"id": user_id}) or []
        return bool(rows and rows[0].get("ai_paused"))
    except Exception as e:
        logger.warning(f"User AI pause check failed (non-blocking): {e}")
        return False


def is_ai_paused(user_id: Optional[str] = None) -> bool:
    """True when the AI must stay silent for this user (or globally for the
    legacy operator path when user_id is unknown)."""
    if _global_paused():
        return True
    if user_id:
        return _user_paused(user_id)
    return False


def set_ai_pause(paused: bool, user_id: str, is_admin: bool = False) -> Dict[str, Any]:
    """Sets the pause for the session user; admins also control the global
    legacy-operation switch (they operate the env-connected pages)."""
    try:
        supabase_db.update("users", user_id, {"ai_paused": bool(paused)})
    except Exception as e:
        logger.error(f"Failed to persist user AI pause: {e}")
        raise

    global_set = False
    if is_admin:
        try:
            supabase_db.set_setting(GLOBAL_PAUSE_KEY, bool(paused))
            global_set = True
        except Exception as e:
            logger.error(f"Failed to persist global AI pause: {e}")

    return {
        "user_paused": bool(paused),
        "global_paused": _global_paused(),
        "global_set": global_set,
    }


def pause_status(user_id: str, is_admin: bool = False) -> Dict[str, Any]:
    return {
        "user_paused": _user_paused(user_id) if user_id else False,
        "global_paused": _global_paused(),
        "effective_paused": is_ai_paused(user_id),
    }

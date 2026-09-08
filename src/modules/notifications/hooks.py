"""
Notification hooks — fire in-app notifications when background JOBS complete.

Integrated at real execution points (WS-F owner requirement):
  - content publish jobs (scheduler / publish-now)
  - meta syncs (feed / insights)
  - automations executions (comment-to-DM)
  - onboarding saves

Design: wrapper around background task callables. A notification failure
NEVER breaks the business operation (notifications are a courtesy — the
operation result is the source of truth).
"""
from typing import Any, Dict, Optional

from src.core.logger import logger


def _notify_admin(title: str, body: str, ntype: str = "info", meta: Optional[Dict[str, Any]] = None):
    """Fires a notification to every active admin (owner watches site activity)."""
    try:
        from src.core.supabase_client import supabase_db
        from src.modules.notifications.service import notification_service
        admins = supabase_db.select("users", {"role": "admin"}) or []
        for a in admins:
            if a.get("is_active"):
                notification_service.create(a["id"], title, body, ntype, meta or {})
    except Exception as e:
        logger.warning(f"notify_admin failed (non-blocking): {e}")


def notify_job_result(user_id: Optional[str], job_name: str, ok: bool,
                      detail: str = "", meta: Optional[Dict[str, Any]] = None):
    """Generic completion notification for a user's own job."""
    if not user_id:
        return
    try:
        from src.modules.notifications.service import notification_service
        notification_service.create(
            user_id,
            f"{'✅' if ok else '⚠️'} {job_name}",
            detail,
            "success" if ok else "warning",
            {"job": job_name, **(meta or {})},
        )
    except Exception as e:
        logger.warning(f"notify_job_result failed (non-blocking): {e}")


def hook_publish_job(task_fn):
    """Decorator: wraps an async publish task; notifies admins on completion."""
    async def wrapper(*args, **kwargs):
        try:
            result = await task_fn(*args, **kwargs)
            try:
                status = (result or {}).get("status") if isinstance(result, dict) else None
                ok = status in (None, "success", "published")
                _notify_admin(
                    "📣 نشر محتوى" if ok else "⚠️ فشل نشر محتوى",
                    f"نتيجة: {status or 'منجز'}",
                    "success" if ok else "warning",
                    {"job": "publish", "result": result if isinstance(result, dict) else None},
                )
            except Exception as ne:
                logger.warning(f"publish hook notify failed: {ne}")
            return result
        except Exception as e:
            _notify_admin("⛔ خطأ في نشر محتوى", str(e)[:200], "error", {"job": "publish"})
            raise
    wrapper.__name__ = getattr(task_fn, "__name__", "wrapped_publish")
    return wrapper


def notify_sync_result(kind: str, result: Dict[str, Any]):
    """Called inline after a sync completes (feed/insights). Notifies admins honestly."""
    try:
        status = result.get("status")
        if status == "success":
            if kind == "feed":
                _notify_admin("🔄 مزامنة المحتوى", f"تمت المزامنة: {result.get('total_synced', 0)} منشور", "success",
                              {"job": "feed_sync", "total": result.get("total_synced", 0)})
            elif kind == "insights":
                _notify_admin("📈 مزامنة الإحصائيات", "تم تحديث مؤشرات الأداء", "success", {"job": "insights"})
        elif status in ("skipped", "no_results"):
            pass  # honest skip — no noise
        else:
            _notify_admin(f"⚠️ مزامنة {kind}", f"حالة: {status}", "warning", {"job": f"sync_{kind}"})
    except Exception as e:
        logger.warning(f"notify_sync_result failed (non-blocking): {e}")

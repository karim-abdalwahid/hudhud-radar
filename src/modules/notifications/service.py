"""
Notifications service — create/read in-app notifications.

Server-side helper used by job hooks and modules. One source of truth:
the `notifications` table. Zero fabrication: only real events create
notifications. (Email delivery rides on this table later, v1.1.)
"""
from typing import Any, Dict, List, Optional

from src.core.logger import logger
from src.core.supabase_client import supabase_db

VALID_TYPES = ("info", "success", "warning", "error", "broadcast")


class NotificationService:
    """Thin, testable wrapper over the notifications table."""

    def create(
        self,
        user_id: str,
        title: str,
        body: str = "",
        type: str = "info",
        meta: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Creates one notification. FAIL-SILENT by design: a notification
        failure must never break the business operation that triggered it —
        the operation result is the source of truth, the notification is a
        courtesy. Failures are logged for observability."""
        if type not in VALID_TYPES:
            type = "info"
        try:
            return supabase_db.insert("notifications", {
                "user_id": user_id,
                "type": type,
                "title": title[:255],
                "body": body or "",
                "meta": meta or {},
            })
        except Exception as e:
            logger.warning(f"Notification create failed (non-blocking): {e}")
            return None

    def list_for_user(self, user_id: str, limit: int = 30, unread_only: bool = False) -> List[Dict[str, Any]]:
        try:
            rows = supabase_db.select("notifications", {"user_id": user_id}) or []
            rows.sort(key=lambda r: r.get("created_at") or "", reverse=True)
            if unread_only:
                rows = [r for r in rows if not r.get("read")]
            return rows[:limit]
        except Exception as e:
            logger.warning(f"Notification list failed (non-blocking): {e}")
            return []

    def unread_count(self, user_id: str) -> int:
        try:
            rows = supabase_db.select("notifications", {"user_id": user_id}) or []
            return sum(1 for r in rows if not r.get("read"))
        except Exception:
            return 0

    def mark_read(self, user_id: str, notification_id: str) -> bool:
        try:
            if not supabase_db.select("notifications", {"id": notification_id, "user_id": user_id}):
                return False
            supabase_db.update("notifications", notification_id, {"read": True})
            return True
        except Exception as e:
            logger.warning(f"Notification mark_read failed: {e}")
            return False

    def mark_all_read(self, user_id: str) -> int:
        try:
            rows = supabase_db.select("notifications", {"user_id": user_id}) or []
            count = 0
            for r in rows:
                if not r.get("read"):
                    supabase_db.update("notifications", r["id"], {"read": True})
                    count += 1
            return count
        except Exception as e:
            logger.warning(f"Notification mark_all_read failed: {e}")
            return 0

    def broadcast(self, title: str, body: str = "", type: str = "broadcast",
                  target_user_id: Optional[str] = None) -> int:
        """Admin broadcast: to ALL users or a specific one (owner requirement)."""
        try:
            if target_user_id:
                self.create(target_user_id, title, body, type, {"broadcast": True})
                return 1
            users = supabase_db.select("users", {}) or []
            count = 0
            for u in users:
                if u.get("is_active"):
                    self.create(u["id"], title, body, type, {"broadcast": True})
                    count += 1
            return count
        except Exception as e:
            logger.warning(f"Broadcast failed: {e}")
            return 0


notification_service = NotificationService()

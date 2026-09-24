"""
Notifications service — create/read in-app notifications.

Server-side helper used by job hooks and modules. One source of truth:
the `notifications` table. Zero fabrication: only real events create
notifications. (Email delivery rides on this table later, v1.1.)
"""
import re
from typing import Any, Dict, List, Optional

from src.core.logger import logger
from src.core.supabase_client import supabase_db

VALID_TYPES = ("info", "success", "warning", "error", "broadcast")


def localize_notification(row: Dict[str, Any], lang: str = "en") -> Dict[str, Any]:
    """Translates/localizes a notification record according to the target language ('en' or 'ar')."""
    if not row or lang not in ("en", "ar"):
        return row

    res = dict(row)
    meta = res.get("meta") or {}
    title = str(res.get("title") or "")
    body = str(res.get("body") or "")

    if lang == "en":
        # 1. Direct metadata overrides if stored
        if meta.get("title_en"):
            res["title"] = meta["title_en"]
        if meta.get("body_en"):
            res["body"] = meta["body_en"]

        if meta.get("title_en") and meta.get("body_en"):
            return res

        # 2. Template-based resolution
        template_key = meta.get("template")
        if template_key:
            try:
                from src.modules.templates_manager import DEFAULT_TEMPLATES, _fill_placeholders
                tmpl = DEFAULT_TEMPLATES.get(template_key)
                if tmpl:
                    if not meta.get("title_en") and tmpl.get("subject_en"):
                        res["title"] = _fill_placeholders(tmpl["subject_en"], meta)
                    if not meta.get("body_en") and tmpl.get("body_en"):
                        res["body"] = _fill_placeholders(tmpl["body_en"], meta)
                    return res
            except Exception:
                pass

        # 3. Dynamic pattern resolution for existing Arabic notifications
        t = res["title"]
        b = res["body"]

        # Welcome notifications:
        m = re.search(r"أهلاً بك (?:في|إلى) هدهد[،\s]+يا?\s*(.+?)!?", t)
        if m:
            user_name = m.group(1).strip()
            res["title"] = f"🎉 Welcome to Hudhud, {user_name}!"
            res["body"] = "Your account is ready. Next step: connect your social channels from Settings to activate automated replies."
            return res

        # Plan activations:
        if "تم تفعيل" in t:
            plan_name = t.replace("✅", "").replace("تم تفعيل", "").replace("خطتك:", "").replace("باقة", "").strip()
            res["title"] = f"✅ Plan activated: {plan_name}" if plan_name else "✅ Plan activated"
            if "المنصات المشمولة" in b:
                p_match = re.search(r"المنصات المشمولة في خطتك:\s*([^.]+)", b)
                platforms = p_match.group(1).strip() if p_match else "All channels"
                res["body"] = f"Included platforms: {platforms}. AI credits have been updated."
            else:
                res["body"] = "Your plan is active and AI credits have been added to your balance."
            return res

        # Trial started:
        if "بدأت تجربتك المجانية" in t:
            res["title"] = "✅ Your free trial has started"
            res["body"] = "All messaging channels are available for 3 days."
            return res

        # Subscription canceled:
        if "تم إلغاء اشتراكك" in t:
            res["title"] = "⚠️ Subscription canceled"
            res["body"] = "Channels paused — activate a plan to resume automated service."
            return res

        # Credit grant:
        if "تم إضافة" in t and "رصيد" in t:
            c_match = re.search(r"(\d+)", t)
            amount = c_match.group(1) if c_match else meta.get("amount", "")
            res["title"] = f"⚡ Added {amount} AI credits" if amount else "⚡ Added AI credits"
            tot_match = re.search(r"الآن:\s*(\d+)", b)
            tot = tot_match.group(1) if tot_match else ""
            res["body"] = f"Credits successfully added to your account. Your new total: {tot} points." if tot else "Credits successfully added to your account."
            return res

        # Low credits:
        if "رصيد الذكاء الاصطناعي منخفض" in t:
            c_match = re.search(r"(\d+)", b)
            credits_val = c_match.group(1) if c_match else meta.get("credits", "")
            res["title"] = "⚠️ Low AI credits warning"
            res["body"] = f"You have {credits_val} credits remaining. The agent will fall back to static templates when depleted."
            return res

        # Credits exhausted:
        if "رصيد الردود الآلية خلص" in t:
            res["title"] = "⚠️ Out of AI credits"
            res["body"] = "The AI agent has temporarily paused automated replies because your AI credits are exhausted. New messages will still arrive in your inbox for manual replies."
            return res

        # New lead:
        if "عميل محتمل جديد" in t:
            lead_name = meta.get("lead_name", "")
            res["title"] = "🎯 New qualified lead captured!"
            res["body"] = f"Your AI agent captured a new prospect: {lead_name} — view details in your Leads CRM." if lead_name else "Your AI agent captured a new prospect — view details in your Leads CRM."
            return res

    elif lang == "ar":
        if meta.get("title_ar"):
            res["title"] = meta["title_ar"]
        if meta.get("body_ar"):
            res["body"] = meta["body_ar"]

        if meta.get("title_ar") and meta.get("body_ar"):
            return res

        template_key = meta.get("template")
        if template_key:
            try:
                from src.modules.templates_manager import DEFAULT_TEMPLATES, _fill_placeholders
                tmpl = DEFAULT_TEMPLATES.get(template_key)
                if tmpl:
                    if not meta.get("title_ar") and tmpl.get("subject_ar"):
                        res["title"] = _fill_placeholders(tmpl["subject_ar"], meta)
                    if not meta.get("body_ar") and tmpl.get("body_ar"):
                        res["body"] = _fill_placeholders(tmpl["body_ar"], meta)
                    return res
            except Exception:
                pass

    return res


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

    def list_for_user(self, user_id: str, limit: int = 30, unread_only: bool = False, lang: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            rows = supabase_db.select("notifications", {"user_id": user_id}) or []
            rows.sort(key=lambda r: r.get("created_at") or "", reverse=True)
            if unread_only:
                rows = [r for r in rows if not r.get("read")]
            limited = rows[:limit]
            if lang in ("en", "ar"):
                return [localize_notification(r, lang) for r in limited]
            return limited
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

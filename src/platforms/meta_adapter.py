"""
Meta platform adapter — wraps the existing meta_api singletons behind the
PlatformAdapter contract. Delegation only: no behavior changes, zero risk.
"""
from typing import Any, Dict, List

from src.platforms.base import PlatformAdapter, PlatformCapabilities, PlatformStatus


class MetaPlatformAdapter(PlatformAdapter):
    """Facebook Page + Instagram (both share the Meta Graph integration)."""

    def __init__(self, name: str, display_name: str):
        self.name = name
        self.display_name = display_name
        self.capabilities = PlatformCapabilities(
            messaging=True, comments=True, publishing=True,
            insights=True, oauth=False,  # Meta uses token exchange, not per-user OAuth yet
            webhooks=True, compliance_callbacks=True,
        )

    def get_status(self) -> PlatformStatus:
        # Real status from the existing health pipeline (cached, honest).
        from src.core.admin_alerts import collect_alerts
        try:
            alerts = collect_alerts()
            meta = next((a for a in alerts if a.get("id") == "meta_token"), {})
            webhook = next((a for a in alerts if a.get("id") == "webhook"), {})
            valid = meta.get("level") == "ok"
            return PlatformStatus(
                connected=valid,
                configured=bool(meta.get("level") != "warning" or valid),
                details={"webhook": webhook.get("level"), "token": meta.get("level")},
            )
        except Exception:
            return PlatformStatus(connected=False, configured=False)

    def fetch_posts(self, limit: int = 25) -> List[Dict[str, Any]]:
        from src.meta_api.feed_sync import meta_feed_sync
        platform = "instagram" if self.name == "instagram" else "facebook"
        return meta_feed_sync.get_synced_posts(platform=platform, limit=limit) or []

    def fetch_insights(self, days: int = 7) -> Dict[str, Any]:
        # Real sync (writes metrics) is driven by cron; this returns recent rows.
        from src.core.supabase_client import supabase_db
        rows = supabase_db.select("page_performance_metrics", {"platform": self.name}) or []
        return {"platform": self.name, "days": days, "metrics": rows}

    def verify_webhook_signature(self, payload_bytes: bytes, signature: Optional[str] = None) -> bool:
        from src.meta_api.webhooks import webhook_handler
        return webhook_handler.verify_signature(payload_bytes, signature)

"""
Threads platform adapter — wraps the existing Threads OAuth/publisher code
behind the PlatformAdapter contract. Delegation only: no behavior changes.
"""
from typing import Optional

from src.meta_api.threads_oauth import threads_oauth
from src.platforms.base import PlatformAdapter, PlatformCapabilities, PlatformStatus


class ThreadsPlatformAdapter(PlatformAdapter):
    def __init__(self):
        self.name = "threads"
        self.display_name = "Threads"
        self.capabilities = PlatformCapabilities(
            messaging=False,  # Threads has no DM API — replies/comments only
            comments=True, publishing=True, insights=True,
            oauth=True, webhooks=False, compliance_callbacks=True,
        )

    def get_status(self) -> PlatformStatus:
        try:
            s = threads_oauth.get_status()
            expires_at = None
            creds = s.get("details") or {}
            if s.get("expires_in_days") is not None:
                import time as _time
                expires_at = _time.time() + float(s["expires_in_days"]) * 86400
            return PlatformStatus(
                connected=bool(s.get("connected")),
                configured=bool(s.get("configured")),
                username=s.get("username"),
                expires_at=expires_at,
            )
        except Exception:
            return PlatformStatus(connected=False, configured=False)

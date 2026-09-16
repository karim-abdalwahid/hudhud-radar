"""
Threads platform adapter — wraps the existing Threads OAuth/publisher code
behind the PlatformAdapter contract. Delegation only: no behavior changes.
"""
from typing import Optional

from src.config import settings
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
        # PlatformAdapter has no tenant/session argument, so it cannot safely
        # inspect a customer's connection. Connection status is exposed via
        # the tenant-bound /api/threads/status route instead.
        return PlatformStatus(
            connected=False,
            configured=bool(settings.THREADS_APP_ID and settings.THREADS_APP_SECRET),
        )

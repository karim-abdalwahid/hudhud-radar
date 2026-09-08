"""
Platform Adapter Contract — how a social platform plugs into Hudhud.

To add a NEW platform (e.g. TikTok, LinkedIn, WhatsApp Business):
  1. Create src/platforms/<name>/ implementing PlatformAdapter.
  2. Register it in src/platforms/registry.py.
  3. DB migration: ALTER TYPE platform_enum ADD VALUE '<name>';
     (documented in database/migrations — one line, safe, non-breaking)

Everything else (inbox, feed sync, analytics, compliance) consumes the
REGISTRY — never concrete platform classes. This is what keeps platform
addition clean and non-breaking (owner architecture requirement).
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PlatformCapabilities:
    """What a platform adapter supports — UI/UX gates on this, never on isinstance()."""
    messaging: bool = False          # can send/receive DMs
    comments: bool = False           # can read/reply to comments
    publishing: bool = False         # can schedule & publish posts
    insights: bool = False           # has performance metrics
    oauth: bool = False              # has an OAuth connect flow
    webhooks: bool = False           # has inbound event webhooks
    compliance_callbacks: bool = False  # data deletion / uninstall callbacks


@dataclass
class PlatformStatus:
    connected: bool = False
    configured: bool = False
    username: Optional[str] = None
    expires_at: Optional[float] = None
    details: Dict[str, Any] = field(default_factory=dict)


class PlatformAdapter(ABC):
    """Abstract contract. Implement ONLY what the platform supports and
    reflect it in `capabilities`; unsupported methods raise NotImplementedError."""

    name: str = ""                     # registry key, e.g. "facebook" (matches platform_enum)
    display_name: str = ""             # e.g. "Facebook Page"
    capabilities: PlatformCapabilities = PlatformCapabilities()

    # ---- Connection lifecycle -------------------------------------------------
    @abstractmethod
    def get_status(self) -> PlatformStatus:
        """Live connection status for dashboards/alerts. Must never raise."""

    # ---- Content & engagement (optional by capability) ------------------------
    def fetch_posts(self, limit: int = 25) -> List[Dict[str, Any]]:
        """Normalized posts: id, text, created_time, comments[], media_type."""
        raise NotImplementedError(f"{self.name} does not support fetch_posts")

    def send_message(self, recipient_id: str, text: str, **kwargs) -> Dict[str, Any]:
        raise NotImplementedError(f"{self.name} does not support send_message")

    def publish_post(self, content: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError(f"{self.name} does not support publish_post")

    def fetch_insights(self, days: int = 7) -> Dict[str, Any]:
        raise NotImplementedError(f"{self.name} does not support fetch_insights")

    # ---- Inbound verification (optional by capability) ------------------------
    def verify_webhook_signature(self, payload_bytes: bytes, signature: Optional[str]) -> bool:
        raise NotImplementedError(f"{self.name} does not support webhooks")

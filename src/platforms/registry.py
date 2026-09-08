"""
Platform Registry — THE single lookup for everything platform-related.

Consumers (inbox, feed sync, analytics, future modules) MUST resolve
platforms through get_adapter()/adapters() — never import platform
singletons directly. That is what makes adding a platform non-breaking:

  1) src/platforms/<name>_adapter.py implementing PlatformAdapter
  2) one line in PLATFORM_ADAPTERS below
  3) database/migrations: ALTER TYPE platform_enum ADD VALUE '<name>';
"""
from typing import Dict, Optional

from src.platforms.base import PlatformAdapter
from src.platforms.meta_adapter import MetaPlatformAdapter
from src.platforms.threads_adapter import ThreadsPlatformAdapter

PLATFORM_ADAPTERS: Dict[str, PlatformAdapter] = {
    "facebook": MetaPlatformAdapter("facebook", "Facebook Page"),
    "instagram": MetaPlatformAdapter("instagram", "Instagram Business"),
    "threads": ThreadsPlatformAdapter(),
}


def get_adapter(platform: str) -> Optional[PlatformAdapter]:
    return PLATFORM_ADAPTERS.get((platform or "").lower())


def adapters() -> Dict[str, PlatformAdapter]:
    return dict(PLATFORM_ADAPTERS)


def supported_platforms() -> list:
    return sorted(PLATFORM_ADAPTERS.keys())

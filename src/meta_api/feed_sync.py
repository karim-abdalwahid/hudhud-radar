"""
Legacy Feed Sync Compatibility Stub.
Tenant feed synchronization is now handled securely by TenantFeedService
(src/modules/meta/tenant_feed_service.py) with per-user encrypted credentials.
"""
from typing import List, Dict, Any, Optional
from src.core.logger import logger


class MetaLiveFeedSync:
    """Compatibility shim for legacy unscoped feed sync imports."""

    def __init__(self):
        self._cached_posts: List[Dict[str, Any]] = []
        self._cache_updated_at: Optional[str] = None

    def get_synced_posts(
        self,
        platform: Optional[str] = None,
        post_type: Optional[str] = None,
        limit: int = 150,
    ) -> List[Dict[str, Any]]:
        """Global feed is retired; returns empty to protect tenant isolation."""
        return []

    def get_cache_metadata(self) -> Dict[str, Any]:
        return {
            "total": 0,
            "facebook_count": 0,
            "instagram_count": 0,
            "reels_count": 0,
            "posts_count": 0,
            "cache_updated_at": None,
        }

    async def sync_all_live_content(self, limit_per_platform: int = 100) -> Dict[str, Any]:
        return {
            "status": "skipped",
            "reason": "Global Meta feed sync is disabled; use tenant_feed_service.",
            "facebook_count": 0,
            "instagram_count": 0,
            "total_synced": 0,
            "cache_updated_at": None,
            "posts": [],
        }


meta_feed_sync = MetaLiveFeedSync()

"""Tenant-isolated Live Posts & Media Synchronization Service.

Fetches and normalizes published posts, reels, and media across Facebook,
Instagram, and Threads specifically scoped to the authenticated tenant user.
Ensures strict multi-tenant isolation by resolving per-user encrypted tokens.
"""
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import httpx

from src.config import settings
from src.core.logger import logger
from src.modules.connections.service import connection_service


class TenantFeedService:
    """Service to fetch and normalize feeds for an authenticated tenant."""

    async def get_tenant_posts(
        self,
        user_id: str,
        platform: str = "all",
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Fetches posts across connected platforms for the given user_id."""
        if not user_id:
            return []

        tasks = []
        platform_lower = (platform or "all").lower()

        async with httpx.AsyncClient(timeout=12.0) as client:
            if platform_lower in ("all", "facebook", "fb"):
                tasks.append(self._fetch_facebook_posts(client, user_id, limit))
            if platform_lower in ("all", "instagram", "ig"):
                tasks.append(self._fetch_instagram_media(client, user_id, limit))
            if platform_lower in ("all", "threads"):
                tasks.append(self._fetch_threads_posts(client, user_id, limit))

            results = await asyncio.gather(*tasks, return_exceptions=True)

        all_posts: List[Dict[str, Any]] = []
        for r in results:
            if isinstance(r, list):
                all_posts.extend(r)
            elif isinstance(r, Exception):
                logger.warning("Error fetching tenant feed: %s", r)

        # Sort descending by published_at / created_time
        all_posts.sort(key=lambda x: str(x.get("published_at") or ""), reverse=True)
        return all_posts[:limit]

    async def _fetch_facebook_posts(
        self,
        client: httpx.AsyncClient,
        user_id: str,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Fetches Facebook Page posts for the user."""
        creds = connection_service.get_publish_credentials(user_id, "facebook")
        if not creds or not creds.get("access_token") or not creds.get("account_id"):
            return []

        token = creds["access_token"]
        page_id = creds["account_id"]
        url = f"{settings.META_GRAPH_API_BASE_URL}/{page_id}/posts"
        params = {
            "fields": "id,message,created_time,full_picture,permalink_url,shares,reactions.summary(true),comments.summary(true)",
            "limit": min(limit, 50),
            "access_token": token,
        }

        try:
            resp = await client.get(url, params=params)
            if resp.status_code != 200:
                logger.warning("Facebook posts fetch failed for user %s: HTTP %s", user_id, resp.status_code)
                return []
            data = resp.json().get("data", [])
            normalized = []
            for item in data:
                text = item.get("message") or ""
                created_at = item.get("created_time") or ""
                shares_cnt = (item.get("shares") or {}).get("count", 0)
                reactions_cnt = (item.get("reactions") or {}).get("summary", {}).get("total_count", 0)
                comments_cnt = (item.get("comments") or {}).get("summary", {}).get("total_count", 0)
                pic = item.get("full_picture")

                normalized.append({
                    "id": str(item.get("id")),
                    "platform": "facebook",
                    "post_type": "post",
                    "content_text": text,
                    "message": text,
                    "caption": text,
                    "published_at": created_at,
                    "created_time": created_at,
                    "thumbnail_url": pic,
                    "media_url": pic,
                    "permalink": item.get("permalink_url"),
                    "likes_count": reactions_cnt,
                    "comments_count": comments_cnt,
                    "shares_count": shares_cnt,
                    "views_count": None,
                })
            return normalized
        except Exception as e:
            logger.warning("Error querying Facebook Graph API for user %s: %s", user_id, e)
            return []

    async def _fetch_instagram_media(
        self,
        client: httpx.AsyncClient,
        user_id: str,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Fetches Instagram Media/Reels for the user's connected Instagram account."""
        creds = connection_service.get_publish_credentials(user_id, "instagram")
        if not creds or not creds.get("access_token") or not creds.get("account_id"):
            return []

        token = creds["access_token"]
        ig_id = creds["account_id"]
        url = f"{settings.META_GRAPH_API_BASE_URL}/{ig_id}/media"
        params = {
            "fields": "id,caption,media_type,media_url,thumbnail_url,permalink,timestamp,like_count,comments_count",
            "limit": min(limit, 50),
            "access_token": token,
        }

        try:
            resp = await client.get(url, params=params)
            if resp.status_code != 200:
                logger.warning("Instagram media fetch failed for user %s: HTTP %s", user_id, resp.status_code)
                return []
            data = resp.json().get("data", [])
            normalized = []
            for item in data:
                m_type = (item.get("media_type") or "IMAGE").upper()
                is_reel = (m_type == "VIDEO")
                text = item.get("caption") or ""
                created_at = item.get("timestamp") or ""
                thumb = item.get("thumbnail_url") or item.get("media_url")

                normalized.append({
                    "id": str(item.get("id")),
                    "platform": "instagram",
                    "post_type": "reel" if is_reel else "post",
                    "content_text": text,
                    "message": text,
                    "caption": text,
                    "published_at": created_at,
                    "created_time": created_at,
                    "thumbnail_url": thumb,
                    "media_url": item.get("media_url"),
                    "permalink": item.get("permalink"),
                    "likes_count": item.get("like_count", 0),
                    "comments_count": item.get("comments_count", 0),
                    "shares_count": 0,
                    "views_count": None,
                })
            return normalized
        except Exception as e:
            logger.warning("Error querying Instagram Graph API for user %s: %s", user_id, e)
            return []

    async def _fetch_threads_posts(
        self,
        client: httpx.AsyncClient,
        user_id: str,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Fetches published Threads for the user's connected account."""
        token = connection_service.get_active_token(user_id, "threads")
        if not token:
            return []

        url = f"{settings.THREADS_BASE_URL}/me/threads"
        params = {
            "fields": "id,text,timestamp,media_type,media_url,permalink",
            "limit": min(limit, 50),
            "access_token": token,
        }

        try:
            resp = await client.get(url, params=params)
            if resp.status_code != 200:
                logger.warning("Threads fetch failed for user %s: HTTP %s", user_id, resp.status_code)
                return []
            data = resp.json().get("data", [])
            normalized = []
            for item in data:
                text = item.get("text") or ""
                created_at = item.get("timestamp") or ""
                media_url = item.get("media_url")

                normalized.append({
                    "id": str(item.get("id")),
                    "platform": "threads",
                    "post_type": "post",
                    "content_text": text,
                    "message": text,
                    "caption": text,
                    "published_at": created_at,
                    "created_time": created_at,
                    "thumbnail_url": media_url,
                    "media_url": media_url,
                    "permalink": item.get("permalink"),
                    "likes_count": 0,
                    "comments_count": 0,
                    "shares_count": 0,
                    "views_count": None,
                })
            return normalized
        except Exception as e:
            logger.warning("Error querying Threads API for user %s: %s", user_id, e)
            return []


tenant_feed_service = TenantFeedService()

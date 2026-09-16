"""
Meta Live Posts & Reels Synchronization Service.
Fetches, caches, and syncs real published Facebook posts and Instagram Reels/Media
directly from Meta Graph API v26.0 using the connected Page and Business Account credentials.
"""
from typing import List, Dict, Any, Optional
import httpx
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path

from src.config import settings
from src.core.logger import logger
from src.meta_api.rate_limiter import rate_limiter

CACHE_FILE = Path(__file__).resolve().parent.parent / "knowledge" / "meta_live_cache.json"


class MetaLiveFeedSync:
    """Retired unscoped Meta-feed service.

    It is retained only so legacy imports fail safely while per-tenant feed
    synchronization is designed.  It must never read deployment credentials
    or a shared cache, because either would mix customer accounts.
    """

    def __init__(self):
        self._cached_posts: List[Dict[str, Any]] = []
        self._cache_updated_at: Optional[str] = None

    @property
    def base_url(self) -> str:
        return settings.META_GRAPH_API_BASE_URL

    def _get_credentials(self) -> Dict[str, str]:
        """Never supply credentials to the former global feed path."""
        return {"token": "", "page_id": "", "ig_id": ""}

    def _load_cache_from_disk(self):
        """Do not load tenantless historical Meta data."""
        self._cached_posts = []
        self._cache_updated_at = None

    def _save_cache_to_disk(self):
        """No-op: shared local/cloud Meta caches are prohibited."""
        return None

    async def _fetch_facebook_video_metrics(self, client: httpx.AsyncClient, video_id: str, token: str) -> Dict[str, Any]:
        """Fetches real views, picture thumbnail, and likes/comments counts for a specific Facebook video/reel object."""
        try:
            url = f"{self.base_url}/{video_id}"
            params = {
                "fields": "id,views,picture,thumbnails{uri,is_preferred,width,height},likes.summary(true),comments.summary(true)",
                "access_token": token
            }
            res = await client.get(url, params=params)
            if res.status_code == 200:
                data = res.json()
                views = data.get("views", 0) or 0
                likes = data.get("likes", {}).get("summary", {}).get("total_count", 0) or 0
                comments = data.get("comments", {}).get("summary", {}).get("total_count", 0) or 0

                # Prefer the largest available thumbnail for high-quality display
                picture = None
                thumbnails = data.get("thumbnails", {}).get("data", [])
                if thumbnails:
                    # Sort by width descending to get the highest-resolution thumbnail
                    sorted_thumbs = sorted(thumbnails, key=lambda t: t.get("width", 0), reverse=True)
                    preferred = next((t.get("uri") for t in sorted_thumbs if t.get("is_preferred")), None)
                    largest = sorted_thumbs[0].get("uri") if sorted_thumbs else None
                    picture = preferred or largest

                # Fall back to the small 'picture' field only as secondary fallback
                fallback_picture = data.get("picture")

                return {"views": views, "likes": likes, "comments": comments, "picture": picture, "fallback_picture": fallback_picture}
        except Exception as e:
            logger.debug(f"Error fetching FB video metrics for {video_id}: {e}")
        return {"views": 0, "likes": 0, "comments": 0, "picture": None, "fallback_picture": None}

    async def fetch_facebook_reels(
        self,
        limit: int = 100,
        shares_by_target: Optional[Dict[str, int]] = None,
        thumbnails_by_target: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """Fetches real published video reels directly from Facebook Page video_reels endpoint with thumbnails and live metrics."""
        creds = self._get_credentials()
        page_id = creds["page_id"]
        token = creds["token"]
        if not page_id or not token or token.startswith("your-"):
            return []

        shares_map = shares_by_target or {}
        thumbs_map = thumbnails_by_target or {}

        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                url = f"{self.base_url}/{page_id}/video_reels"
                params = {
                    "fields": "id,video_id,description,created_time,permalink_url",
                    "limit": limit,
                    "access_token": token
                }
                resp = await client.get(url, params=params)
                if resp.status_code != 200:
                    logger.error(f"Failed to fetch FB video_reels: {resp.text}")
                    return []

                data = resp.json().get("data", [])
                
                # Concurrently enrich all reels with views, pictures, likes, and comments
                sem = asyncio.Semaphore(10)
                async def enrich_reel(item):
                    reel_id = str(item.get("id") or item.get("video_id") or "")
                    if not reel_id:
                        return None
                    video_id = str(item.get("video_id") or reel_id)
                    desc = item.get("description") or ""
                    purl = item.get("permalink_url") or f"/reel/{reel_id}/"
                    if not purl.startswith("http"):
                        purl = f"https://www.facebook.com{purl}"

                    async with sem:
                        metrics = await self._fetch_facebook_video_metrics(client, video_id, token)

                    thumb_url = metrics.get("picture") or thumbs_map.get(reel_id) or thumbs_map.get(video_id) or metrics.get("fallback_picture")
                    shares = shares_map.get(reel_id) or shares_map.get(video_id) or 0
                    comments = metrics.get("comments", 0)

                    return {
                        "id": reel_id,
                        "video_id": video_id,
                        "platform": "facebook",
                        "post_type": "reel",
                        "content_text": desc,
                        "thumbnail_url": thumb_url,
                        "media_url": thumb_url,
                        "permalink": purl,
                        "published_at": item.get("created_time"),
                        "likes_count": metrics.get("likes", 0),
                        "comments_count": comments,
                        "shares_count": shares,
                        "views_count": metrics.get("views", 0),
                        "is_live_meta": True
                    }

                tasks = [enrich_reel(item) for item in data]
                results = await asyncio.gather(*tasks)
                return [r for r in results if r is not None]
        except Exception as e:
            logger.error(f"Error fetching FB video_reels: {e}")
            return []

    async def fetch_facebook_posts(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetches real published posts from Facebook Page with live attachments, shares, and permalinks."""
        creds = self._get_credentials()
        page_id = creds["page_id"]
        token = creds["token"]
        if not page_id or not token or token.startswith("your-"):
            logger.warning("Facebook Page credentials missing or mock.")
            return []

        rate_limiter.check_and_acquire("facebook")
        url = f"{self.base_url}/{page_id}/published_posts"
        params = {
            "fields": "id,message,created_time,permalink_url,full_picture,shares,likes.summary(true),comments.summary(true),attachments{media_type,type,url,unshimmed_url,title,target}",
            "limit": limit,
            "access_token": token
        }

        posts = []
        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                resp = await client.get(url, params=params)
                rate_limiter.update_from_headers("facebook", dict(resp.headers))
                if resp.status_code != 200:
                    logger.error(f"Failed to fetch Facebook posts: {resp.text}")
                    return []

                data = resp.json().get("data", [])
                for item in data:
                    caption = item.get("message") or ""
                    shares = item.get("shares", {}).get("count", 0) or 0
                    likes = item.get("likes", {}).get("summary", {}).get("total_count", 0) or 0
                    comments = item.get("comments", {}).get("summary", {}).get("total_count", 0) or 0
                    attachments = item.get("attachments", {}).get("data", [])
                    
                    is_reel = False
                    video_id = None
                    permalink = item.get("permalink_url") or f"https://facebook.com/{item['id']}"

                    for att in attachments:
                        att_url = att.get("url", "") or att.get("unshimmed_url", "")
                        att_type = att.get("type", "")
                        if "/reel/" in att_url or att_type in ["video_inline", "video"]:
                            is_reel = True
                            if not permalink or "facebook.com/" in permalink:
                                if att_url:
                                    permalink = att_url
                            video_id = att.get("target", {}).get("id")
                            break

                    posts.append({
                        "id": item["id"],
                        "video_id": video_id,
                        "platform": "facebook",
                        "post_type": "reel" if is_reel else "post",
                        "content_text": caption,
                        "thumbnail_url": item.get("full_picture"),
                        "media_url": item.get("full_picture"),
                        "permalink": permalink,
                        "published_at": item.get("created_time"),
                        "likes_count": likes,
                        "comments_count": comments,
                        "shares_count": shares,
                        "views_count": 0,
                        "is_live_meta": True
                    })
                return posts
        except Exception as e:
            logger.error(f"Error querying Facebook Graph API: {e}")
            return []

    async def fetch_instagram_media(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetches real published reels and media from Instagram Business Account with like and comment counts."""
        creds = self._get_credentials()
        ig_id = creds["ig_id"]
        token = creds["token"]
        if not ig_id or not token or token.startswith("your-"):
            logger.warning("Instagram Account ID missing or mock.")
            return []

        rate_limiter.check_and_acquire("instagram")
        url = f"{self.base_url}/{ig_id}/media"
        params = {
            "fields": "id,caption,media_type,media_product_type,media_url,thumbnail_url,permalink,timestamp,like_count,comments_count",
            "limit": limit,
            "access_token": token
        }

        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                resp = await client.get(url, params=params)
                rate_limiter.update_from_headers("instagram", dict(resp.headers))
                if resp.status_code != 200:
                    logger.error(f"Failed to fetch Instagram media: {resp.text}")
                    return []

                data = resp.json().get("data", [])
                items = []
                video_media_ids = []
                for item in data:
                    mtype = (item.get("media_type") or "VIDEO").upper()
                    product_type = (item.get("media_product_type") or "").upper()
                    permalink = item.get("permalink") or f"https://instagram.com/p/{item['id']}"
                    is_reel = (product_type == "REELS") or (mtype == "VIDEO") or ("/reel/" in permalink)
                    thumb = item.get("thumbnail_url") or item.get("media_url")
                    if is_reel:
                        video_media_ids.append(str(item["id"]))

                    items.append({
                        "id": str(item["id"]),
                        "platform": "instagram",
                        "post_type": "reel" if is_reel else "post",
                        "content_text": item.get("caption") or "",
                        "thumbnail_url": thumb,
                        "media_url": item.get("media_url") or thumb,
                        "permalink": permalink,
                        "published_at": item.get("timestamp"),
                        "likes_count": item.get("like_count", 0) or 0,
                        "comments_count": item.get("comments_count", 0) or 0,
                        "shares_count": 0,
                        "views_count": 0,
                        "is_live_meta": True
                    })

                # Real view counts via the official IG Insights API
                # (views metric, plays fallback) — Zero-Fabrication: when the
                # API returns nothing, the count stays 0, never invented.
                if video_media_ids:
                    views_by_id = await self._fetch_ig_media_views(
                        client, token, video_media_ids)
                    for item in items:
                        if item["id"] in views_by_id:
                            item["views_count"] = views_by_id[item["id"]]
                return items
        except Exception as e:
            logger.error(f"Error querying Instagram Graph API: {e}")
            return []

    async def _fetch_ig_media_views(self, client: httpx.AsyncClient, token: str,
                                    media_ids: List[str]) -> Dict[str, int]:
        """Fetches real view counts for IG reels/videos via the Insights API.
        Primary metric: views. Fallback: plays (older reels). Idempotent + rate-limited."""
        views: Dict[str, int] = {}
        for mid in media_ids:
            try:
                rate_limiter.check_and_acquire("instagram")
                for metric in ("views", "plays"):
                    resp = await client.get(
                        f"{self.base_url}/{mid}/insights",
                        params={"metric": metric, "access_token": token},
                    )
                    if resp.status_code == 200:
                        rows = resp.json().get("data", [])
                        for row in rows:
                            for v in row.get("values", []):
                                val = v.get("value", 0) or 0
                                if val > views.get(mid, 0):
                                    views[mid] = int(val)
                        if mid in views:
                            break
                    elif resp.status_code == 429:
                        rate_limiter.update_from_headers("instagram", dict(resp.headers))
                        break
            except Exception as e:
                logger.warning(f"IG insights fetch skipped for {mid}: {e}")
        return views

    async def sync_all_live_content(self, limit_per_platform: int = 100) -> Dict[str, Any]:
        """Refuse global synchronization until a tenant-aware replacement exists."""
        return {
            "status": "skipped",
            "reason": "Global Meta feed sync is disabled; use a tenant-scoped connection.",
            "facebook_count": 0,
            "instagram_count": 0,
            "total_synced": 0,
            "cache_updated_at": None,
            "posts": [],
        }

        # Historical implementation below is intentionally unreachable until
        # it is replaced with user_id-bound credentials and storage.
        # 1. First fetch FB posts to extract shares mapping, thumbnails mapping, and additional posts
        fb_posts = await self.fetch_facebook_posts(limit=limit_per_platform)
        shares_by_target: Dict[str, int] = {}
        thumbnails_by_target: Dict[str, str] = {}
        for p in fb_posts:
            s_count = p.get("shares_count", 0)
            p_thumb = p.get("thumbnail_url")
            v_id = p.get("video_id")
            p_id = p.get("id")
            if v_id:
                if s_count:
                    shares_by_target[str(v_id)] = s_count
                if p_thumb:
                    thumbnails_by_target[str(v_id)] = p_thumb
            if p_id and p_thumb:
                thumbnails_by_target[str(p_id)] = p_thumb

        # 2. Fetch FB Reels directly with real views, likes, comments, and thumbnails
        fb_reels = await self.fetch_facebook_reels(
            limit=limit_per_platform,
            shares_by_target=shares_by_target,
            thumbnails_by_target=thumbnails_by_target
        )

        # 3. Fetch IG Reels and media
        ig_posts = await self.fetch_instagram_media(limit=limit_per_platform)

        # Merge FB items: prioritize fb_reels, then append unique fb_posts
        seen_keys = set()
        unique_fb = []

        # Add FB reels first
        for r in fb_reels:
            r_id = str(r.get("id", ""))
            v_id = str(r.get("video_id") or "")
            text_snip = (r.get("content_text") or "").strip()[:40]
            if r_id:
                seen_keys.add(r_id)
            if v_id:
                seen_keys.add(v_id)
            if text_snip:
                seen_keys.add(f"txt_{text_snip}")
            unique_fb.append(r)

        # Add any non-duplicate published posts
        for p in fb_posts:
            p_id = str(p.get("id", ""))
            v_id = str(p.get("video_id") or "")
            text_snip = (p.get("content_text") or "").strip()[:40]

            key = v_id if v_id else p_id
            if key and key in seen_keys:
                continue
            if text_snip and f"txt_{text_snip}" in seen_keys:
                continue

            if key:
                seen_keys.add(key)
            if v_id:
                seen_keys.add(v_id)
            if p_id:
                seen_keys.add(p_id)
            if text_snip:
                seen_keys.add(f"txt_{text_snip}")

        # Cross-enrich Facebook items with high-resolution Instagram thumbnails for identical cross-posted reels
        ig_thumbs_by_text = {}
        for ig in ig_posts:
            ithumb = ig.get("thumbnail_url")
            icontent = (ig.get("content_text") or "").strip()[:40]
            if ithumb and icontent and "_p160x160_" not in ithumb:
                ig_thumbs_by_text[icontent] = ithumb

        for fb in unique_fb:
            fthumb = fb.get("thumbnail_url") or ""
            fcontent = (fb.get("content_text") or "").strip()[:40]
            if fcontent in ig_thumbs_by_text:
                if not fthumb or "_p160x160_" in fthumb or "_p130x130_" in fthumb:
                    fb["thumbnail_url"] = ig_thumbs_by_text[fcontent]
                    fb["media_url"] = ig_thumbs_by_text[fcontent]

        combined = unique_fb + ig_posts
        # Sort descending by published_at
        combined.sort(key=lambda x: x.get("published_at") or "", reverse=True)

        if combined:
            self._cached_posts = combined
            self._cache_updated_at = datetime.now(timezone.utc).isoformat()
            self._save_cache_to_disk()
            logger.info(f"Successfully synced {len(combined)} live Meta posts/reels (FB: {len(unique_fb)}, IG: {len(ig_posts)})")

        # HONEST STATUS: success only if something was actually fetched.
        # Previously returned "success" even when every platform fetch failed,
        # masking total outages (e.g., dead token) as healthy syncs.
        if not combined:
            return {
                "status": "no_results",
                "reason": "لم يتم سحب أي منشورات — تحقق من صلاحية Meta Token والاتصال",
                "facebook_count": len(unique_fb),
                "instagram_count": len(ig_posts),
                "total_synced": 0,
                "cache_updated_at": self._cache_updated_at,
                "posts": self._cached_posts,
            }

        return {
            "status": "success",
            "facebook_count": len(unique_fb),
            "instagram_count": len(ig_posts),
            "total_synced": len(combined),
            "cache_updated_at": self._cache_updated_at,
            "posts": combined
        }

    def get_synced_posts(
        self,
        platform: Optional[str] = None,
        post_type: Optional[str] = None,
        limit: int = 150
    ) -> List[Dict[str, Any]]:
        """No global Meta archive is available to a tenant."""
        return []

    def get_cache_metadata(self) -> Dict[str, Any]:
        """Returns cache statistics and last-sync timestamp."""
        return {
            "total": 0,
            "facebook_count": 0,
            "instagram_count": 0,
            "reels_count": 0,
            "posts_count": 0,
            "cache_updated_at": None,
        }


meta_feed_sync = MetaLiveFeedSync()

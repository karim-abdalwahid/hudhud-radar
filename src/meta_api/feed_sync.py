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
    """Synchronizes and serves real published posts and reels from Meta Graph API."""

    def __init__(self):
        self._cached_posts: List[Dict[str, Any]] = []
        self._cache_updated_at: Optional[str] = None
        self._load_cache_from_disk()

    @property
    def base_url(self) -> str:
        return settings.META_GRAPH_API_BASE_URL

    def _get_credentials(self) -> Dict[str, str]:
        """Resolves active Meta credentials dynamically from Supabase or settings."""
        token = settings.META_PAGE_ACCESS_TOKEN or ""
        page_id = settings.META_PAGE_ID or ""
        ig_id = settings.META_INSTAGRAM_ACCOUNT_ID or ""
        try:
            from src.core.supabase_client import supabase_db
            cached = supabase_db.get_setting("meta_credentials")
            if cached and isinstance(cached, dict):
                token = cached.get("page_access_token") or token
                page_id = cached.get("page_id") or page_id
                ig_id = cached.get("instagram_account_id") or ig_id
        except Exception as e:
            logger.debug(f"Could not load dynamic credentials from Supabase: {e}")
        return {"token": token, "page_id": page_id, "ig_id": ig_id}

    def _load_cache_from_disk(self):
        """Loads cached posts from Supabase cloud or disk cache."""
        # 1. Check Supabase cloud cache first (holds full archive of 121+ items with real views)
        try:
            from src.core.supabase_client import supabase_db
            data = supabase_db.get_setting("meta_cached_posts")
            if data and isinstance(data, dict):
                posts = data.get("posts", [])
                if len(posts) > len(self._cached_posts):
                    self._cached_posts = posts
                    self._cache_updated_at = data.get("updated_at")
        except Exception as e:
            logger.debug(f"Could not load meta posts from Supabase: {e}")

        # 2. Fallback to local disk file if Supabase not loaded
        if not self._cached_posts and CACHE_FILE.exists():
            try:
                data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
                self._cached_posts = data.get("posts", [])
                self._cache_updated_at = data.get("updated_at")
            except Exception as e:
                logger.error(f"Error loading live meta posts cache from disk: {e}")

    def _save_cache_to_disk(self):
        """Persists cached posts to disk and Supabase for instant rendering."""
        payload = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "total_count": len(self._cached_posts),
            "posts": self._cached_posts
        }
        try:
            CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            CACHE_FILE.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            logger.error(f"Error saving live meta posts cache to disk: {e}")

        try:
            from src.core.supabase_client import supabase_db
            supabase_db.set_setting("meta_cached_posts", payload)
        except Exception as e:
            logger.error(f"Error saving live meta posts cache to Supabase: {e}")

    async def _fetch_facebook_video_metrics(self, client: httpx.AsyncClient, video_id: str, token: str) -> Dict[str, Any]:
        """Fetches real views, picture thumbnail, and likes count for a specific Facebook video/reel object."""
        try:
            url = f"{self.base_url}/{video_id}"
            params = {
                "fields": "id,views,picture,likes.summary(true)",
                "access_token": token
            }
            res = await client.get(url, params=params)
            if res.status_code == 200:
                data = res.json()
                views = data.get("views", 0) or 0
                likes = data.get("likes", {}).get("summary", {}).get("total_count", 0) or 0
                picture = data.get("picture")
                return {"views": views, "likes": likes, "comments": 0, "picture": picture}
        except Exception as e:
            logger.debug(f"Error fetching FB video metrics for {video_id}: {e}")
        return {"views": 0, "likes": 0, "comments": 0, "picture": None}

    async def fetch_facebook_reels(self, limit: int = 100, shares_by_target: Optional[Dict[str, int]] = None, max_total: int = 5000) -> List[Dict[str, Any]]:
        """Fetches real published video reels directly from Facebook Page video_reels endpoint with thumbnails and live metrics, automatically paginating through all available reels."""
        creds = self._get_credentials()
        page_id = creds["page_id"]
        token = creds["token"]
        if not page_id or not token or token.startswith("your-"):
            return []

        shares_map = shares_by_target or {}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{self.base_url}/{page_id}/video_reels"
                params = {
                    "fields": "id,video_id,description,created_time,permalink_url",
                    "limit": min(limit, 100),
                    "access_token": token
                }
                raw_items = []
                while url and len(raw_items) < max_total:
                    resp = await client.get(url, params=params)
                    if resp.status_code != 200:
                        logger.error(f"Failed to fetch FB video_reels: {resp.text}")
                        break

                    data = resp.json()
                    items = data.get("data", [])
                    if not items:
                        break
                    raw_items.extend(items)
                    url = data.get("paging", {}).get("next")
                    params = None
                
                # Concurrently enrich all reels with views, pictures, and likes
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

                    thumb_url = metrics.get("picture")
                    shares = shares_map.get(reel_id) or shares_map.get(video_id) or 0

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
                        "comments_count": 0,
                        "shares_count": shares,
                        "views_count": metrics.get("views", 0),
                        "is_live_meta": True
                    }

                tasks = [enrich_reel(item) for item in raw_items]
                results = await asyncio.gather(*tasks)
                return [r for r in results if r is not None]
        except Exception as e:
            logger.error(f"Error fetching FB video_reels: {e}")
            return []

    async def fetch_facebook_posts(self, limit: int = 100, max_total: int = 5000) -> List[Dict[str, Any]]:
        """Fetches real published posts from Facebook Page with live attachments, shares, and permalinks, automatically paginating through all available posts."""
        creds = self._get_credentials()
        page_id = creds["page_id"]
        token = creds["token"]
        if not page_id or not token or token.startswith("your-"):
            logger.warning("Facebook Page credentials missing or mock.")
            return []

        rate_limiter.check_and_acquire("facebook")
        url = f"{self.base_url}/{page_id}/published_posts"
        params = {
            "fields": "id,message,created_time,permalink_url,full_picture,shares,attachments{media_type,type,url,unshimmed_url,title,target}",
            "limit": min(limit, 100),
            "access_token": token
        }

        posts = []
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                while url and len(posts) < max_total:
                    resp = await client.get(url, params=params)
                    rate_limiter.update_from_headers("facebook", dict(resp.headers))
                    if resp.status_code != 200:
                        logger.error(f"Failed to fetch Facebook posts: {resp.text}")
                        break

                    data = resp.json()
                    items = data.get("data", [])
                    if not items:
                        break

                    for item in items:
                        caption = item.get("message") or ""
                        shares = item.get("shares", {}).get("count", 0) or 0
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
                            "likes_count": 0,
                            "comments_count": 0,
                            "shares_count": shares,
                            "views_count": 0,
                            "is_live_meta": True
                        })

                    url = data.get("paging", {}).get("next")
                    params = None

                return posts
        except Exception as e:
            logger.error(f"Error querying Facebook Graph API: {e}")
            return []

    async def fetch_instagram_media(self, limit: int = 100, max_total: int = 5000) -> List[Dict[str, Any]]:
        """Fetches real published reels and media from Instagram Business Account with like and comment counts, automatically paginating through all available media."""
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
            "limit": min(limit, 100),
            "access_token": token
        }

        items = []
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                while url and len(items) < max_total:
                    resp = await client.get(url, params=params)
                    rate_limiter.update_from_headers("instagram", dict(resp.headers))
                    if resp.status_code != 200:
                        logger.error(f"Failed to fetch Instagram media: {resp.text}")
                        break

                    data = resp.json()
                    raw_list = data.get("data", [])
                    if not raw_list:
                        break

                    for item in raw_list:
                        mtype = (item.get("media_type") or "VIDEO").upper()
                        product_type = (item.get("media_product_type") or "").upper()
                        permalink = item.get("permalink") or f"https://instagram.com/p/{item['id']}"
                        
                        is_reel = (product_type == "REELS") or (mtype == "VIDEO") or ("/reel/" in permalink)
                        post_type = "reel" if is_reel else "post"
                        thumb = item.get("thumbnail_url") or item.get("media_url")

                        items.append({
                            "id": str(item["id"]),
                            "platform": "instagram",
                            "post_type": post_type,
                            "content_text": item.get("caption") or "",
                            "thumbnail_url": thumb,
                            "media_url": item.get("media_url"),
                            "permalink": permalink,
                            "published_at": item.get("timestamp"),
                            "likes_count": item.get("like_count", 0) or 0,
                            "comments_count": item.get("comments_count", 0) or 0,
                            "shares_count": 0,
                            "views_count": 0,
                            "is_live_meta": True
                        })

                    url = data.get("paging", {}).get("next")
                    params = None

                return items
        except Exception as e:
            logger.error(f"Error querying Instagram Graph API: {e}")
            return []

    async def sync_all_live_content(self, limit_per_platform: int = 100) -> Dict[str, Any]:
        """Fetches from Facebook (all video reels & posts) and Instagram (all reels & media), strictly deduplicates, and caches."""
        # 1. First fetch FB posts to extract shares mapping and additional posts
        fb_posts = await self.fetch_facebook_posts(limit=limit_per_platform)
        shares_by_target: Dict[str, int] = {}
        for p in fb_posts:
            s_count = p.get("shares_count", 0)
            v_id = p.get("video_id")
            if v_id and s_count:
                shares_by_target[str(v_id)] = s_count

        # 2. Fetch FB Reels directly with real views, likes, and thumbnails
        fb_reels = await self.fetch_facebook_reels(limit=limit_per_platform, shares_by_target=shares_by_target)

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

            unique_fb.append(p)

        combined = unique_fb + ig_posts
        # Sort descending by published_at
        combined.sort(key=lambda x: x.get("published_at") or "", reverse=True)

        if combined:
            self._cached_posts = combined
            self._cache_updated_at = datetime.now(timezone.utc).isoformat()
            self._save_cache_to_disk()
            logger.info(f"Successfully synced {len(combined)} live Meta posts/reels (FB: {len(unique_fb)}, IG: {len(ig_posts)})")

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
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Returns currently cached real posts with optional platform and post_type filters."""
        if not self._cached_posts:
            self._load_cache_from_disk()
        posts = self._cached_posts
        if platform and platform != "all":
            posts = [p for p in posts if p.get("platform") == platform]
        if post_type and post_type != "all":
            posts = [p for p in posts if p.get("post_type") == post_type]
        if limit is not None and limit > 0:
            return posts[:limit]
        return posts

    def get_cache_metadata(self) -> Dict[str, Any]:
        """Returns cache statistics and last-sync timestamp."""
        if not self._cached_posts:
            self._load_cache_from_disk()
        fb = [p for p in self._cached_posts if p.get("platform") == "facebook"]
        ig = [p for p in self._cached_posts if p.get("platform") == "instagram"]
        reels = [p for p in self._cached_posts if p.get("post_type") == "reel"]
        normal_posts = [p for p in self._cached_posts if p.get("post_type") == "post"]
        return {
            "total": len(self._cached_posts),
            "facebook_count": len(fb),
            "instagram_count": len(ig),
            "reels_count": len(reels),
            "posts_count": len(normal_posts),
            "cache_updated_at": self._cache_updated_at
        }


meta_feed_sync = MetaLiveFeedSync()

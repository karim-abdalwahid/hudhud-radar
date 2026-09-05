"""
Meta Live Posts & Reels Synchronization Service.
Fetches, caches, and syncs real published Facebook posts and Instagram Reels/Media
directly from Meta Graph API using the connected Page and Business Account credentials.
"""
from typing import List, Dict, Any, Optional
import httpx
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
        self.base_url = settings.META_GRAPH_API_BASE_URL
        self._cached_posts: List[Dict[str, Any]] = []
        self._cache_updated_at: Optional[str] = None
        self._load_cache_from_disk()

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
        """Loads cached posts from disk or Supabase if available."""
        if CACHE_FILE.exists():
            try:
                data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
                self._cached_posts = data.get("posts", [])
                self._cache_updated_at = data.get("updated_at")
            except Exception as e:
                logger.error(f"Error loading live meta posts cache from disk: {e}")

        # Fallback to Supabase cloud cache (crucial for Vercel serverless cold starts)
        if not self._cached_posts:
            try:
                from src.core.supabase_client import supabase_db
                data = supabase_db.get_setting("meta_cached_posts")
                if data and isinstance(data, dict):
                    self._cached_posts = data.get("posts", [])
                    self._cache_updated_at = data.get("updated_at")
            except Exception as e:
                logger.debug(f"Could not load meta posts from Supabase: {e}")

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

    async def _fetch_facebook_video_metrics(self, client: httpx.AsyncClient, video_id: str, token: str) -> Dict[str, int]:
        """Fetches views, likes, and comments count for a specific Facebook video/reel object."""
        try:
            url = f"{self.base_url}/{video_id}"
            params = {
                "fields": "id,views,likes.summary(true),comments.summary(true)",
                "access_token": token
            }
            res = await client.get(url, params=params)
            if res.status_code == 200:
                data = res.json()
                views = data.get("views", 0) or 0
                likes = data.get("likes", {}).get("summary", {}).get("total_count", 0) or 0
                comments = data.get("comments", {}).get("summary", {}).get("total_count", 0) or 0
                return {"views": views, "likes": likes, "comments": comments}
        except Exception as e:
            logger.debug(f"Error fetching FB video metrics for {video_id}: {e}")
        return {"views": 0, "likes": 0, "comments": 0}

    async def fetch_facebook_posts(self, limit: int = 25) -> List[Dict[str, Any]]:
        """Fetches real published posts and reels from Facebook Page with live engagement metrics."""
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
            async with httpx.AsyncClient(timeout=18.0) as client:
                resp = await client.get(url, params=params)
                rate_limiter.update_from_headers("facebook", dict(resp.headers))
                if resp.status_code != 200:
                    logger.warning(f"published_posts with summary fields returned HTTP {resp.status_code}. Retrying with standard fields...")
                    fallback_params = {
                        "fields": "id,message,created_time,permalink_url,full_picture,shares,attachments{media_type,type,url,unshimmed_url,title,target}",
                        "limit": limit,
                        "access_token": token
                    }
                    resp = await client.get(url, params=fallback_params)
                    if resp.status_code != 200:
                        logger.error(f"Failed to fetch Facebook posts on fallback: {resp.text}")
                        return []

                data = resp.json().get("data", [])
                for item in data:
                    caption = item.get("message") or ""
                    shares = item.get("shares", {}).get("count", 0) or 0
                    direct_likes = item.get("likes", {}).get("summary", {}).get("total_count", 0) or 0
                    direct_comments = item.get("comments", {}).get("summary", {}).get("total_count", 0) or 0
                    likes_count = direct_likes
                    comments_count = direct_comments
                    views_count = 0
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

                    if video_id:
                        metrics = await self._fetch_facebook_video_metrics(client, video_id, token)
                        views_count = metrics["views"]
                        if metrics["likes"] > likes_count:
                            likes_count = metrics["likes"]
                        if metrics["comments"] > comments_count:
                            comments_count = metrics["comments"]

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
                        "likes_count": likes_count,
                        "comments_count": comments_count,
                        "shares_count": shares,
                        "views_count": views_count,
                        "is_live_meta": True
                    })
                return posts
        except Exception as e:
            logger.error(f"Error querying Facebook Graph API: {e}")
            return []

    async def fetch_facebook_reels(self, limit: int = 25, existing_video_ids: Optional[set] = None) -> List[Dict[str, Any]]:
        """Fetches real published video reels directly from Facebook Page video_reels endpoint with thumbnails."""
        creds = self._get_credentials()
        page_id = creds["page_id"]
        token = creds["token"]
        if not page_id or not token or token.startswith("your-"):
            return []

        existing_ids = existing_video_ids or set()

        try:
            async with httpx.AsyncClient(timeout=18.0) as client:
                url = f"{self.base_url}/{page_id}/video_reels"
                params = {
                    "fields": "id,video_id,description,created_time,permalink_url",
                    "limit": limit,
                    "access_token": token
                }
                resp = await client.get(url, params=params)
                if resp.status_code != 200:
                    return []

                data = resp.json().get("data", [])
                reels = []
                for item in data:
                    reel_id = str(item.get("id") or item.get("video_id") or "")
                    if not reel_id or reel_id in existing_ids:
                        continue

                    desc = item.get("description") or ""
                    purl = item.get("permalink_url") or f"/reel/{reel_id}/"
                    if not purl.startswith("http"):
                        purl = f"https://www.facebook.com{purl}"

                    # Fetch real views count & real thumbnail picture from the video object
                    metrics = await self._fetch_facebook_video_metrics(client, reel_id, token)
                    
                    # Fetch real thumbnail picture from Meta Graph API for this reel
                    thumb_url = None
                    try:
                        v_pic_res = await client.get(
                            f"{self.base_url}/{reel_id}",
                            params={"fields": "picture", "access_token": token}
                        )
                        if v_pic_res.status_code == 200:
                            thumb_url = v_pic_res.json().get("picture")
                    except Exception as e:
                        logger.debug(f"Error fetching thumbnail for reel {reel_id}: {e}")

                    reels.append({
                        "id": reel_id,
                        "video_id": reel_id,
                        "platform": "facebook",
                        "post_type": "reel",
                        "content_text": desc,
                        "thumbnail_url": thumb_url,
                        "media_url": thumb_url,
                        "permalink": purl,
                        "published_at": item.get("created_time"),
                        "likes_count": metrics["likes"],
                        "comments_count": metrics["comments"],
                        "shares_count": 0,
                        "views_count": metrics["views"],
                        "is_live_meta": True
                    })
                return reels
        except Exception as e:
            logger.debug(f"Error fetching FB video_reels: {e}")
            return []

    async def _fetch_instagram_video_views(self, client: httpx.AsyncClient, media_id: str, token: str) -> int:
        """Fetches real views or plays for an Instagram Reel/video using Graph API insights."""
        try:
            url = f"{self.base_url}/{media_id}/insights"
            # In Graph API v19-v23, 'plays' is standard for Reels, while 'views'/'impressions' apply to videos/posts
            for metric_name in ["plays", "views", "impressions", "reach"]:
                try:
                    res = await client.get(url, params={"metric": metric_name, "access_token": token})
                    if res.status_code == 200:
                        data = res.json().get("data", [])
                        if data:
                            m = data[0]
                            values = m.get("values", [])
                            if values and values[-1].get("value") is not None:
                                val = int(values[-1].get("value", 0) or 0)
                                if val > 0:
                                    return val
                            total_val = m.get("total_value", {}).get("value")
                            if total_val is not None and int(total_val) > 0:
                                return int(total_val)
                except Exception:
                    continue
        except Exception as e:
            logger.debug(f"Error fetching IG video views for {media_id}: {e}")
        return 0

    async def fetch_instagram_media(self, limit: int = 25) -> List[Dict[str, Any]]:
        """Fetches real published reels and media from Instagram Account with like, comment, and view counts."""
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
            async with httpx.AsyncClient(timeout=18.0) as client:
                resp = await client.get(url, params=params)
                rate_limiter.update_from_headers("instagram", dict(resp.headers))
                if resp.status_code != 200:
                    logger.error(f"Failed to fetch Instagram media: {resp.text}")
                    return []

                data = resp.json().get("data", [])
                items = []
                for item in data:
                    mtype = (item.get("media_type") or "VIDEO").upper()
                    product_type = (item.get("media_product_type") or "").upper()
                    permalink = item.get("permalink") or f"https://instagram.com/p/{item['id']}"
                    
                    is_reel = (product_type == "REELS") or (mtype == "VIDEO") or ("/reel/" in permalink)
                    post_type = "reel" if is_reel else "post"
                    thumb = item.get("thumbnail_url") or item.get("media_url")

                    views_count = 0
                    if is_reel or mtype == "VIDEO":
                        views_count = await self._fetch_instagram_video_views(client, item["id"], token)

                    items.append({
                        "id": item["id"],
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
                        "views_count": views_count,
                        "is_live_meta": True
                    })
                return items
        except Exception as e:
            logger.error(f"Error querying Instagram Graph API: {e}")
            return []

    async def sync_all_live_content(self, limit_per_platform: int = 25) -> Dict[str, Any]:
        """Fetches from Facebook (posts & reels) and Instagram, strictly deduplicates, and caches."""
        fb_posts = await self.fetch_facebook_posts(limit=limit_per_platform)
        
        # Collect video IDs and post IDs already fetched from published_posts
        known_fb_video_ids = set()
        for p in fb_posts:
            if p.get("video_id"):
                known_fb_video_ids.add(str(p["video_id"]))
            known_fb_video_ids.add(str(p["id"]))

        fb_reels = await self.fetch_facebook_reels(limit=limit_per_platform, existing_video_ids=known_fb_video_ids)
        ig_posts = await self.fetch_instagram_media(limit=limit_per_platform)

        # Merge FB items without duplicate video_id, id, or identical content text
        seen_keys = set()
        unique_fb = []
        for p in fb_posts + fb_reels:
            # Create a composite key to prevent duplicates
            p_id = str(p.get("id", ""))
            v_id = str(p.get("video_id") or "")
            text_snippet = (p.get("content_text") or "").strip()[:40]
            
            key = v_id if v_id else p_id
            if key and key in seen_keys:
                continue
            if text_snippet and f"txt_{text_snippet}" in seen_keys:
                continue

            if key:
                seen_keys.add(key)
            if v_id:
                seen_keys.add(v_id)
            if p_id:
                seen_keys.add(p_id)
            if text_snippet:
                seen_keys.add(f"txt_{text_snippet}")

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
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Returns currently cached real posts with optional platform and post_type filters."""
        if not self._cached_posts:
            self._load_cache_from_disk()
        posts = self._cached_posts
        if platform and platform != "all":
            posts = [p for p in posts if p.get("platform") == platform]
        if post_type and post_type != "all":
            posts = [p for p in posts if p.get("post_type") == post_type]
        return posts[:limit]

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

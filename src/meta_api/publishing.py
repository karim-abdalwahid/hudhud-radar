"""
Meta Graph API Content Publisher:
Handles publishing feed posts, photos, videos, Instagram Reels, and Stories.
"""
from typing import Dict, Any, Optional, List
import asyncio
import httpx
from datetime import datetime, timezone

from src.config import settings
from src.core.logger import logger
from src.core.exceptions import MetaAPIError
from src.meta_api.rate_limiter import rate_limiter
from src.content_studio.models import ContentPlatform, PostType, ContentPostResponse


class MetaPublisher:
    """Publishes content to Facebook Page and Instagram Business / Creator accounts."""

    BASE_URL = settings.META_GRAPH_API_BASE_URL

    def __init__(
        self,
        access_token: Optional[str] = None,
        page_id: Optional[str] = None,
        instagram_id: Optional[str] = None,
        facebook_access_token: Optional[str] = None,
        instagram_access_token: Optional[str] = None,
    ):
        # The legacy single token is retained only for local/dev callers. The
        # SaaS scheduler passes both tenant-bound credentials explicitly.
        self.facebook_access_token = facebook_access_token or access_token or settings.META_PAGE_ACCESS_TOKEN
        self.instagram_access_token = instagram_access_token or access_token or settings.META_PAGE_ACCESS_TOKEN
        self.access_token = self.facebook_access_token
        self.page_id = page_id or settings.META_PAGE_ID
        self.instagram_id = instagram_id or settings.META_INSTAGRAM_ACCOUNT_ID

    # -------------------------------------------------------------
    # Facebook Publishing
    # -------------------------------------------------------------
    async def publish_facebook_feed_post(self, message: str, link: Optional[str] = None) -> Dict[str, Any]:
        """Publishes a text post (with optional external link) to the Facebook Page."""
        rate_limiter.check_and_acquire("facebook")
        url = f"{self.BASE_URL}/{self.page_id}/feed"
        payload = {
            "message": message,
            "access_token": self.facebook_access_token,
        }
        if link:
            payload["link"] = link

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, data=payload)
            rate_limiter.update_from_headers("facebook", dict(resp.headers))
            data = resp.json()
            if resp.status_code != 200 or "id" not in data:
                error_msg = data.get("error", {}).get("message", resp.text)
                logger.error(f"Facebook feed publish failed: {error_msg}")
                raise MetaAPIError(f"Facebook Publish Failed: {error_msg}", status_code=resp.status_code)

            logger.info(f"Published Facebook feed post: {data['id']}")
            return {"post_id": data["id"], "platform": "facebook", "type": "feed"}

    async def publish_facebook_photo(self, image_url: str, caption: str) -> Dict[str, Any]:
        """Publishes a photo post with caption to the Facebook Page."""
        rate_limiter.check_and_acquire("facebook")
        url = f"{self.BASE_URL}/{self.page_id}/photos"
        payload = {
            "url": image_url,
            "message": caption,
            "access_token": self.facebook_access_token,
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(url, data=payload)
            rate_limiter.update_from_headers("facebook", dict(resp.headers))
            data = resp.json()
            if resp.status_code != 200 or "id" not in data:
                error_msg = data.get("error", {}).get("message", resp.text)
                logger.error(f"Facebook photo publish failed: {error_msg}")
                raise MetaAPIError(f"Facebook Photo Publish Failed: {error_msg}", status_code=resp.status_code)

            logger.info(f"Published Facebook photo post: {data['id']}")
            return {"post_id": data.get("post_id", data["id"]), "platform": "facebook", "type": "photo"}

    # -------------------------------------------------------------
    # Instagram Publishing (Container Workflow)
    # -------------------------------------------------------------
    async def create_instagram_container(
        self,
        media_url: str,
        caption: str,
        media_type: str = "IMAGE", # IMAGE, REELS, STORIES
    ) -> str:
        """
        Creates an Instagram media container.
        Returns: container_id (creation_id)
        """
        if not self.instagram_id:
            raise MetaAPIError("Instagram Account ID is not configured.")

        rate_limiter.check_and_acquire("instagram")
        url = f"{self.BASE_URL}/{self.instagram_id}/media"
        payload = {
            "access_token": self.instagram_access_token,
        }

        if media_type == "REELS":
            payload["video_url"] = media_url
            payload["media_type"] = "REELS"
            payload["caption"] = caption
            payload["share_to_feed"] = "true"
        elif media_type == "STORIES":
            # Can be image or video
            if media_url.endswith(".mp4") or media_url.endswith(".mov"):
                payload["video_url"] = media_url
            else:
                payload["image_url"] = media_url
            payload["media_type"] = "STORIES"
        else:
            payload["image_url"] = media_url
            payload["caption"] = caption

        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(url, data=payload)
            rate_limiter.update_from_headers("instagram", dict(resp.headers))
            data = resp.json()
            if resp.status_code != 200 or "id" not in data:
                error_msg = data.get("error", {}).get("message", resp.text)
                logger.error(f"Instagram container creation failed: {error_msg}")
                raise MetaAPIError(f"Instagram Container Creation Failed: {error_msg}", status_code=resp.status_code)

            container_id = data["id"]
            logger.info(f"Instagram container created: {container_id} (Type: {media_type})")
            return container_id

    async def wait_for_instagram_container_ready(self, container_id: str, max_retries: int = 15, delay_seconds: int = 3) -> bool:
        """Checks status of video/reels container until FINISHED or ERROR."""
        url = f"{self.BASE_URL}/{container_id}"
        params = {
            "fields": "status_code,status",
            "access_token": self.instagram_access_token,
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            for attempt in range(max_retries):
                resp = await client.get(url, params=params)
                if resp.status_code == 200:
                    status_info = resp.json()
                    status_code = status_info.get("status_code", "").upper()
                    logger.debug(f"Container {container_id} status check #{attempt+1}: {status_code}")

                    if status_code == "FINISHED":
                        return True
                    elif status_code in ["ERROR", "EXPIRED"]:
                        raise MetaAPIError(f"Instagram media processing failed with status: {status_code}")
                
                await asyncio.sleep(delay_seconds)

        return True  # If timeout, try publishing anyway

    async def publish_instagram_container(self, container_id: str) -> Dict[str, Any]:
        """Publishes the previously created and ready Instagram container."""
        rate_limiter.check_and_acquire("instagram")
        url = f"{self.BASE_URL}/{self.instagram_id}/media_publish"
        payload = {
            "creation_id": container_id,
            "access_token": self.instagram_access_token,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, data=payload)
            rate_limiter.update_from_headers("instagram", dict(resp.headers))
            data = resp.json()
            if resp.status_code != 200 or "id" not in data:
                error_msg = data.get("error", {}).get("message", resp.text)
                logger.error(f"Instagram publish failed: {error_msg}")
                raise MetaAPIError(f"Instagram Publish Failed: {error_msg}", status_code=resp.status_code)

            logger.info(f"Published Instagram media: {data['id']}")
            return {"post_id": data["id"], "platform": "instagram"}

    # -------------------------------------------------------------
    # High-level Unified Publisher
    # -------------------------------------------------------------
    async def publish_content(
        self,
        platform: ContentPlatform,
        post_type: PostType,
        text: str,
        media_urls: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Unified publisher handling Facebook, Instagram, or Both.
        Returns combined dictionary with post IDs and status per platform.
        """
        results = {"success": True, "published_ids": {}, "errors": {}}
        media_url = media_urls[0] if media_urls and len(media_urls) > 0 else None

        # 1. Facebook Publishing
        if platform in [ContentPlatform.FACEBOOK, ContentPlatform.BOTH]:
            try:
                if media_url:
                    fb_res = await self.publish_facebook_photo(image_url=media_url, caption=text)
                else:
                    fb_res = await self.publish_facebook_feed_post(message=text)
                results["published_ids"]["facebook"] = fb_res["post_id"]
            except Exception as e:
                logger.error(f"Facebook publish step failed: {e}")
                results["errors"]["facebook"] = str(e)
                results["success"] = False

        # 2. Instagram Publishing
        if platform in [ContentPlatform.INSTAGRAM, ContentPlatform.BOTH]:
            try:
                if not media_url:
                    raise MetaAPIError("Instagram requires at least one media URL (Image or Video) to publish.")
                
                # Determine IG media type
                ig_type = "IMAGE"
                if post_type == PostType.REEL:
                    ig_type = "REELS"
                elif post_type == PostType.STORY:
                    ig_type = "STORIES"

                container_id = await self.create_instagram_container(
                    media_url=media_url,
                    caption=text,
                    media_type=ig_type,
                )

                if ig_type in ["REELS", "STORIES"]:
                    await self.wait_for_instagram_container_ready(container_id)

                ig_res = await self.publish_instagram_container(container_id)
                results["published_ids"]["instagram"] = ig_res["post_id"]
            except Exception as e:
                logger.error(f"Instagram publish step failed: {e}")
                results["errors"]["instagram"] = str(e)
                if platform == ContentPlatform.INSTAGRAM:
                    results["success"] = False

        return results



    # -------------------------------------------------------------
    # Lifecycle: delete a published object (Wave 9.8 — makes "manage
    # posts" TRUE: scheduled drafts are removed locally, published
    # objects are removed from Meta itself)
    # -------------------------------------------------------------
    async def delete_published(self, platform: str, external_id: str) -> Dict[str, Any]:
        """DELETEs a published FB Page post or IG media object via Graph API.
        Honest result dict — never claims success without a 200."""
        platform = (platform or "").lower()
        target = "facebook" if platform in ("facebook", "both") else platform
        if not external_id:
            return {"ok": False, "detail": "no external id"}
        token = self.facebook_access_token if target == "facebook" else self.instagram_access_token
        if not token or token.startswith("your-"):
            return {"ok": False, "detail": "Meta token not configured (fail-closed)"}
        url = f"{self.BASE_URL}/{external_id}"
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.delete(url, params={"access_token": token})
            if resp.status_code == 200:
                logger.info(f"Deleted published {platform} object {external_id} on Meta")
                return {"ok": True}
            logger.warning(f"Meta delete {platform} {external_id} failed: HTTP {resp.status_code} {resp.text[:180]}")
            return {"ok": False, "detail": f"HTTP {resp.status_code}: {resp.text[:180]}"}
        except Exception as e:
            logger.error(f"Meta delete {platform} {external_id} error: {e}")
            return {"ok": False, "detail": str(e)[:180]}

meta_publisher = MetaPublisher()

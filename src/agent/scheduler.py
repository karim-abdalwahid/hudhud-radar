"""
Background Content Publishing Scheduler:
Monitors scheduled posts, reels, and stories, and triggers automated publication at the designated time.
"""
from typing import List, Dict, Any
import asyncio
from datetime import datetime, timezone
import json

from src.core.logger import logger
from src.content_studio.service import ContentStudioService
from src.content_studio.models import ContentStatus, ContentPostUpdate, ContentPostResponse
from src.meta_api.publishing import meta_publisher


class ContentScheduler:
    """Schedules and executes automated publishing of social media posts."""

    def __init__(self, service: ContentStudioService = None, publisher=meta_publisher):
        self.service = service or ContentStudioService()
        self.publisher = publisher
        self.is_running = False
        self._task: asyncio.Task = None

    async def check_and_publish_due_posts(self) -> List[Dict[str, Any]]:
        """
        Scans database for scheduled posts whose execution time has arrived,
        and publishes them to Facebook/Instagram.
        """
        now = datetime.now(timezone.utc)
        scheduled_posts = self.service.list_posts(status=ContentStatus.SCHEDULED)
        
        due_posts = [
            p for p in scheduled_posts
            if p.scheduled_for and p.scheduled_for <= now
        ]

        if not due_posts:
            return []

        logger.info(f"Found {len(due_posts)} due post(s) to publish automatically.")
        results = []

        for post in due_posts:
            res = await self.publish_single_post(post)
            results.append(res)

        return results

    async def publish_single_post(self, post: ContentPostResponse) -> Dict[str, Any]:
        """Publishes a specific post and updates its status in the database."""
        post_id = post.id
        logger.info(f"Publishing post {post_id} ({post.platform.value}, {post.post_type.value})...")
        
        # Ruflo Swarm Gatekeeper: Audit content safety, brand tone, and policy compliance
        from src.content_studio.compliance_agent import compliance_gatekeeper
        verdict = compliance_gatekeeper.audit_content(
            content_text=post.content_text,
            platform=post.platform.value if hasattr(post.platform, 'value') else str(post.platform),
            post_type=post.post_type.value if hasattr(post.post_type, 'value') else str(post.post_type),
            media_urls=post.media_urls
        )

        if not verdict.is_compliant:
            error_reason = f"Ruflo Compliance Rejection: score={verdict.quality_score}, warnings={verdict.warnings}"
            logger.warning(f"Post {post_id} blocked by Compliance Gatekeeper: {error_reason}")
            self.service.update_post(
                post_id,
                ContentPostUpdate(
                    status=ContentStatus.FAILED,
                    error_message=error_reason
                )
            )
            return {
                "post_id": post_id,
                "status": "rejected_by_compliance",
                "verdict": verdict.model_dump()
            }

        # Mark as publishing
        self.service.update_post(post_id, ContentPostUpdate(status=ContentStatus.PUBLISHING))

        try:
            publish_res = await self.publisher.publish_content(
                platform=post.platform,
                post_type=post.post_type,
                text=post.content_text,
                media_urls=post.media_urls,
            )

            if publish_res.get("success", False) or publish_res.get("published_ids"):
                meta_id_str = json.dumps(publish_res.get("published_ids", {}))
                self.service.update_post(
                    post_id,
                    ContentPostUpdate(
                        status=ContentStatus.PUBLISHED,
                        published_at=datetime.now(timezone.utc),
                        meta_post_id=meta_id_str,
                        error_message=json.dumps(publish_res.get("errors", {})) if publish_res.get("errors") else None,
                    )
                )
                logger.info(f"Post {post_id} successfully published! Meta IDs: {meta_id_str}")
                return {"post_id": post_id, "status": "published", "meta_ids": publish_res.get("published_ids")}
            else:
                err_str = json.dumps(publish_res.get("errors", {"error": "Unknown publishing failure"}))
                self.service.update_post(
                    post_id,
                    ContentPostUpdate(
                        status=ContentStatus.FAILED,
                        error_message=err_str,
                    )
                )
                logger.error(f"Post {post_id} failed to publish: {err_str}")
                return {"post_id": post_id, "status": "failed", "error": err_str}

        except Exception as e:
            logger.error(f"Unexpected exception publishing post {post_id}: {e}", exc_info=True)
            self.service.update_post(
                post_id,
                ContentPostUpdate(
                    status=ContentStatus.FAILED,
                    error_message=str(e),
                )
            )
            return {"post_id": post_id, "status": "failed", "error": str(e)}

    async def start_loop(self, interval_seconds: int = 60):
        """Runs periodic worker in background."""
        self.is_running = True
        logger.info(f"Content Scheduler background worker started (Interval: {interval_seconds}s).")
        try:
            while self.is_running:
                try:
                    await self.check_and_publish_due_posts()
                except Exception as e:
                    logger.error(f"Error in scheduler tick: {e}")
                await asyncio.sleep(interval_seconds)
        except asyncio.CancelledError:
            logger.info("Content Scheduler background worker cancelled.")
        finally:
            self.is_running = False

    def stop_loop(self):
        """Stops the background scheduler worker."""
        self.is_running = False
        if self._task and not self._task.done():
            self._task.cancel()


content_scheduler = ContentScheduler()

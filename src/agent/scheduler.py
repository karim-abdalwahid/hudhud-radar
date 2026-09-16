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

    # IG container wait can take MINUTES on Meta's side. Blocking on it makes
    # the cron request exceed the serverless function budget (Vercel kills it
    # -> cron-job.org counts failures and auto-disables the job). The tick is
    # therefore a SHORT state machine: queue container -> poll once per tick ->
    # publish when ready. Plus self-healing requeue for stuck rows.
    IG_MEDIA_TYPES = {"reel": "REELS", "story": "STORIES"}
    MAX_STARTS_PER_TICK = 2
    STUCK_PUBLISHING_MINUTES = 15
    CONTAINER_TICK_LIMIT = 40  # ~40 ticks of patience (~40-80 min)

    def publisher_for_post(self, post: ContentPostResponse):
        """Build a Graph publisher from this post owner's entitled accounts.

        Scheduled work is global by design (cron sees every due row), but the
        Graph credentials must be selected from the row owner, never from a
        process-wide Meta token.
        """
        owner = getattr(post, "user_id", None)
        # An explicitly injected publisher is a test/development seam.  It is
        # never selected in the real scheduled-worker path, which retains the
        # strict owner-bound credential lookup below.
        from src.core.supabase_client import supabase_db
        if self.publisher is not meta_publisher and not supabase_db.is_connected:
            return self.publisher
        if not owner:
            if not supabase_db.is_connected:
                return self.publisher
            raise ValueError("Scheduled post has no tenant owner")
        from src.modules.connections.service import connection_service
        from src.meta_api.publishing import MetaPublisher
        platform = getattr(post.platform, "value", post.platform)
        fb = connection_service.get_publish_credentials(owner, "facebook") \
            if platform in ("facebook", "both") else None
        ig = connection_service.get_publish_credentials(owner, "instagram") \
            if platform in ("instagram", "both") else None
        if platform in ("facebook", "both") and not fb:
            raise ValueError("Active entitled Facebook connection missing for post owner")
        if platform in ("instagram", "both") and not ig:
            raise ValueError("Active entitled Instagram connection missing for post owner")
        return MetaPublisher(
            page_id=fb["account_id"] if fb else None,
            instagram_id=ig["account_id"] if ig else None,
            facebook_access_token=fb["access_token"] if fb else None,
            instagram_access_token=ig["access_token"] if ig else None,
        )

    async def check_and_publish_due_posts(self) -> List[Dict[str, Any]]:
        """Short-budget tick: resume ready containers, requeue stuck posts,
        start at most MAX_STARTS_PER_TICK new due posts. Never blocks long."""
        results: List[Dict[str, Any]] = []
        try:
            posts = self.service.list_posts(limit=100)
        except Exception as e:
            logger.error(f"Scheduler list failed: {e}")
            return [{"status": "error", "detail": str(e)[:200]}]

        results += await self._resume_pending_containers(posts)
        self._requeue_stuck_publishing(posts)

        now = datetime.now(timezone.utc)
        due = [p for p in posts
               if getattr(p.status, "value", p.status) == "scheduled"
               and p.scheduled_for and p.scheduled_for <= now]
        for post in due[:self.MAX_STARTS_PER_TICK]:
            try:
                results.append(await self._start_due_post(post))
            except Exception as e:
                logger.error(f"Scheduler start failed for {post.id}: {e}")
                results.append({"post_id": post.id, "status": "error",
                                "detail": str(e)[:200]})
        return results

    async def _resume_pending_containers(self, posts) -> List[Dict[str, Any]]:
        """Poll each waiting IG container EXACTLY once (fast); publish when ready."""
        out = []
        now = datetime.now(timezone.utc)
        for post in posts:
            if getattr(post.status, "value", post.status) != "publishing":
                continue
            metrics = dict(post.performance_metrics or {})
            cid = metrics.get("ig_container_id")
            if not cid:
                continue  # handled by _requeue_stuck_publishing
            try:
                publisher = self.publisher_for_post(post)
            except Exception as e:
                self.service.update_post(post.id, ContentPostUpdate(
                    status=ContentStatus.FAILED, error_message=str(e)[:300]))
                out.append({"post_id": post.id, "status": "failed", "detail": str(e)[:150]})
                continue
            ready = False
            try:
                ready = await publisher.wait_for_instagram_container_ready(
                    cid, max_retries=1, delay_seconds=0)
            except Exception as e:
                logger.warning(f"Container poll failed for {post.id}: {e}")
            ticks = int(metrics.get("ig_container_ticks", 0)) + 1
            if not ready:
                if ticks > self.CONTAINER_TICK_LIMIT:
                    self.service.update_post(post.id, ContentPostUpdate(
                        status=ContentStatus.FAILED,
                        error_message="Instagram container never became ready (timed out)"))
                    out.append({"post_id": post.id, "status": "failed_container_timeout"})
                else:
                    metrics["ig_container_ticks"] = ticks
                    self.service.update_post(post.id, ContentPostUpdate(
                        performance_metrics=metrics))
                    out.append({"post_id": post.id, "status": "awaiting_container"})
                continue
            try:
                pub = await publisher.publish_instagram_container(cid)
                media_id = str(pub.get("post_id") or pub.get("id") or pub.get("media_id") or pub.get("code") or "")
            except Exception as e:
                self.service.update_post(post.id, ContentPostUpdate(
                    status=ContentStatus.FAILED,
                    error_message=f"IG container publish failed: {str(e)[:200]}"))
                out.append({"post_id": post.id, "status": "failed", "detail": str(e)[:150]})
                continue
            try:
                ids = json.loads(post.meta_post_id or "{}") if post.meta_post_id else {}
                if not isinstance(ids, dict):
                    ids = {}
            except Exception:
                ids = {}
            if media_id:
                ids["instagram"] = media_id
            metrics["ig_container_done"] = True
            self.service.update_post(post.id, ContentPostUpdate(
                status=ContentStatus.PUBLISHED,
                published_at=now,
                meta_post_id=json.dumps(ids),
                performance_metrics=metrics,
            ))
            logger.info(f"Post {post.id} published via container {cid} (ids: {ids})")
            out.append({"post_id": post.id, "status": "published", "meta_ids": ids})
        return out

    def _requeue_stuck_publishing(self, posts) -> None:
        """'publishing' rows with NO container pending and a stale
        updated_at were killed mid-run (function timeout / crash): send back
        to 'scheduled' so the next tick retries them cleanly."""
        now = datetime.now(timezone.utc)
        for post in posts:
            if getattr(post.status, "value", post.status) != "publishing":
                continue
            metrics = post.performance_metrics or {}
            if metrics.get("ig_container_id"):
                continue
            upd = getattr(post, "updated_at", None)
            try:
                if isinstance(upd, str):
                    upd = datetime.fromisoformat(upd.replace("Z", "+00:00"))
                if not upd or upd.tzinfo is None:
                    upd = (upd or now).replace(tzinfo=timezone.utc)
                age_min = (now - upd).total_seconds() / 60
            except Exception:
                age_min = 0
            if age_min >= self.STUCK_PUBLISHING_MINUTES:
                self.service.update_post(post.id, ContentPostUpdate(
                    status=ContentStatus.SCHEDULED))
                logger.info(f"Requeued stuck post {post.id} ({age_min:.0f} min in 'publishing')")

    async def _start_due_post(self, post) -> Dict[str, Any]:
        """Claim (CAS), compliance-gate, then FB publish inline (fast) and/or
        create the IG container (queues; no waiting). Returns a small result."""
        if not self._claim_for_publish(post.id):
            return {"post_id": post.id, "status": "skipped_already_publishing"}
        plat = getattr(post.platform, "value", post.platform)
        ptype = getattr(post.post_type, "value", post.post_type)
        from src.content_studio.compliance_agent import compliance_gatekeeper
        verdict = compliance_gatekeeper.audit_content(
            content_text=post.content_text, platform=str(plat),
            post_type=str(ptype), media_urls=post.media_urls)
        if not verdict.is_compliant:
            reason = f"Compliance rejection: {verdict.warnings}"
            self.service.update_post(post.id, ContentPostUpdate(
                status=ContentStatus.FAILED, error_message=reason[:300]))
            return {"post_id": post.id, "status": "rejected_by_compliance"}
        self.service.update_post(post.id, ContentPostUpdate(status=ContentStatus.PUBLISHING))

        try:
            publisher = self.publisher_for_post(post)
        except Exception as e:
            self.service.update_post(post.id, ContentPostUpdate(
                status=ContentStatus.FAILED, error_message=str(e)[:300]))
            return {"post_id": post.id, "status": "failed", "errors": {"connection": str(e)[:200]}}

        ids, errors = {}, {}
        media = (post.media_urls or [None])[0]
        if str(plat) in ("facebook", "both"):
            # FB publishing is fast and synchronous (one Graph call) — safe to
            # finish inside this tick. Uses the unified publisher path.
            try:
                from src.content_studio.models import ContentPlatform as _CP, PostType as _PT
                fb_res = await publisher.publish_content(
                    platform=_CP.FACEBOOK,
                    post_type=post.post_type,
                    text=post.content_text,
                    media_urls=post.media_urls or [],
                )
                fb_ids = fb_res.get("published_ids") or {}
                if fb_ids.get("facebook"):
                    ids["facebook"] = str(fb_ids["facebook"])
                if fb_res.get("errors"):
                    errors["facebook"] = str(fb_res["errors"])[:200]
            except Exception as e:
                errors["facebook"] = str(e)[:200]
        cid = None
        if str(plat) in ("instagram", "both"):
            if not media:
                errors["instagram"] = "Instagram publishing requires a media URL"
            else:
                try:
                    cid = await publisher.create_instagram_container(
                        media_url=media, caption=post.content_text,
                        media_type=self.IG_MEDIA_TYPES.get(str(ptype), "IMAGE"))
                except Exception as e:
                    errors["instagram"] = str(e)[:200]

        now = datetime.now(timezone.utc)
        if cid:
            self.service.update_post(post.id, ContentPostUpdate(
                status=ContentStatus.PUBLISHING,
                meta_post_id=json.dumps(ids) if ids else None,
                performance_metrics={**(post.performance_metrics or {}),
                                     "ig_container_id": cid, "ig_container_ticks": 0},
                error_message=json.dumps(errors) if errors else None))
            return {"post_id": post.id, "status": "ig_container_queued",
                    "meta_ids": ids}
        if ids:
            self.service.update_post(post.id, ContentPostUpdate(
                status=ContentStatus.PUBLISHED, published_at=now,
                meta_post_id=json.dumps(ids),
                error_message=json.dumps(errors) if errors else None))
            return {"post_id": post.id, "status": "published", "meta_ids": ids}
        self.service.update_post(post.id, ContentPostUpdate(
            status=ContentStatus.FAILED,
            error_message=json.dumps(errors or {"error": "no platform result"})))
        return {"post_id": post.id, "status": "failed", "errors": errors}

    def _claim_for_publish(self, post_id: str) -> bool:
        """Atomic compare-and-swap: flip the row out of any non-publishing
        state to 'publishing'. Returns False when another worker already
        claimed this exact post (double cron tick / double-click protection).
        Memory-mode dev (no client) skips the claim."""
        try:
            from src.core.supabase_client import supabase_db
            if not (supabase_db.is_connected and supabase_db.client):
                return True
            res = supabase_db.client.table("content_posts").update(
                {"status": "publishing"}
            ).eq("id", post_id).neq("status", "publishing").execute()
            return len(res.data or []) == 1
        except Exception as e:
            logger.warning(f"publish claim check failed (proceeding): {e}")
            return True

    async def publish_single_post(self, post: ContentPostResponse,
                                  allow_inflight: bool = False) -> Dict[str, Any]:
        """Publishes a specific post and updates its status in the database.

        Concurrency guard (audit 2026-09-12): without an explicit
        allow_inflight (used only by the fresh create->publish path where the
        row was just inserted as 'publishing' in this same request), the post is
        atomically claimed first — a duplicate scheduler tick or a double-click
        on Publish Now can no longer publish the same content twice."""
        post_id = post.id
        if not allow_inflight and not self._claim_for_publish(post_id):
            logger.info(f"Post {post_id} publish skipped: already claimed/in flight.")
            return {"post_id": post_id, "status": "skipped_already_publishing"}
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
            publisher = self.publisher_for_post(post)
            publish_res = await publisher.publish_content(
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

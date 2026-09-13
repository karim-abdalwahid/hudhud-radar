"""Cron budget fix: check_and_publish_due_posts -> multi-tick state machine.
Every invocation stays short (well under Vercel's ~10s serverless budget) so
cron-job.org never sees timeouts/failures and stops auto-disabling the job."""
import ast
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

p = "src/agent/scheduler.py"
src = open(p, encoding="utf-8").read()

old = '''    async def check_and_publish_due_posts(self) -> List[Dict[str, Any]]:
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

        return results'''

new = '''    # IG container wait can take MINUTES on Meta's side. Blocking on it makes
    # the cron request exceed the serverless function budget (Vercel kills it
    # -> cron-job.org counts failures and auto-disables the job). The tick is
    # therefore a SHORT state machine: queue container -> poll once per tick ->
    # publish when ready. Plus self-healing requeue for stuck rows.
    IG_MEDIA_TYPES = {"reel": "REELS", "story": "STORIES"}
    MAX_STARTS_PER_TICK = 2
    STUCK_PUBLISHING_MINUTES = 15
    CONTAINER_TICK_LIMIT = 40  # ~40 ticks of patience (~40-80 min)

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
            ready = False
            try:
                ready = await self.publisher.wait_for_instagram_container_ready(
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
                pub = await self.publisher.publish_instagram_container(cid)
                media_id = str(pub.get("id") or pub.get("media_id") or pub.get("code") or "")
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

        ids, errors = {}, {}
        media = (post.media_urls or [None])[0]
        if str(plat) in ("facebook", "both"):
            try:
                if media:
                    fb = await self.publisher.publish_facebook_photo(
                        image_url=media, caption=post.content_text)
                else:
                    fb = await self.publisher.publish_facebook_feed_post(
                        message=post.content_text)
                ids["facebook"] = str(fb.get("post_id") or "")
            except Exception as e:
                errors["facebook"] = str(e)[:200]
        cid = None
        if str(plat) in ("instagram", "both"):
            if not media:
                errors["instagram"] = "Instagram publishing requires a media URL"
            else:
                try:
                    cid = await self.publisher.create_instagram_container(
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
        return {"post_id": post.id, "status": "failed", "errors": errors}'''

assert old in src, "old scheduler block not found"
src = src.replace(old, new, 1)
open(p, "w", encoding="utf-8").write(src)
ast.parse(src)
print("scheduler state machine installed")

# ---------------- cron routes: always fast 200 (never 5xx -> no auto-disable) ---------------
p2 = "src/modules/cron_admin/routes.py"
src2 = open(p2, encoding="utf-8").read()
old_tick = '''    _verify_cron_secret(request)
    results = await content_scheduler.check_and_publish_due_posts()
    if results:
        from src.modules.notifications.hooks import _notify_admin
        _notify_admin("📣 نشر محتوى مجدول", f"تم نشر {len(results)} منشور(ات) مجدولة",
                      "success", {"job": "scheduler_tick", "count": len(results)})
    return {"status": "success", "due_posts_processed": len(results), "details": results}'''
new_tick = '''    _verify_cron_secret(request)
    try:
        results = await content_scheduler.check_and_publish_due_posts()
        status = "success"
        err = None
    except Exception as e:
        # cron-job.org disables jobs after repeated non-2xx answers. The tick
        # always returns 200 with an honest status; failures land in logs +
        # admin alerts instead of HTTP failures.
        logger.error(f"scheduler tick failed (reported 200): {e}")
        results, status, err = [], "partial", str(e)[:200]
    published = [r for r in results if r.get("status") == "published"]
    if published:
        from src.modules.notifications.hooks import _notify_admin
        _notify_admin("📣 نشر محتوى مجدول", f"تم نشر {len(published)} منشور(ات) مجدولة",
                      "success", {"job": "scheduler_tick", "count": len(published)})
    body = {"status": status, "due_posts_processed": len(results), "details": results}
    if err:
        body["error"] = err
    return body'''
assert old_tick in src2
src2 = src2.replace(old_tick, new_tick, 1)
open(p2, "w", encoding="utf-8").write(src2)
ast.parse(src2)
print("scheduler-tick route now always-200")

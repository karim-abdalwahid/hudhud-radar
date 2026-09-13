"""Truth-audit Phase 4 fixes (backend only, zero UI impact):
1. publish_single_post: atomic DB claim (CAS) prevents double-publish races.
2. event_dedup: duplicate-key conflict means ALREADY claimed — do not disable DB dedup."""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ---------- 1. scheduler CAS claim ----------
p = "src/agent/scheduler.py"
src = open(p, encoding="utf-8").read()
old = '''    async def publish_single_post(self, post: ContentPostResponse) -> Dict[str, Any]:
        """Publishes a specific post and updates its status in the database."""
        post_id = post.id
        logger.info(f"Publishing post {post_id} ({post.platform.value}, {post.post_type.value})...")'''
new = '''    def _claim_for_publish(self, post_id: str) -> bool:
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
        logger.info(f"Publishing post {post_id} ({post.platform.value}, {post.post_type.value})...")'''
assert old in src
src = src.replace(old, new, 1)
open(p, "w", encoding="utf-8").write(src)
import ast
ast.parse(src)
print("1. CAS claim added to publish_single_post")

# create route passes allow_inflight (its row is intentionally 'publishing' from birth)
p2 = "src/modules/content/routes.py"
s2 = open(p2, encoding="utf-8").read()
old2 = '''    post = content_studio_service.create_post(payload, user_id=user_id)
    if payload.status == ContentStatus.PUBLISHING:
        background_tasks.add_task(content_scheduler.publish_single_post, post)'''
new2 = '''    post = content_studio_service.create_post(payload, user_id=user_id)
    if payload.status == ContentStatus.PUBLISHING:
        # fresh row created as 'publishing' in this same request -> pre-claimed
        background_tasks.add_task(
            lambda: content_scheduler.publish_single_post(post, allow_inflight=True))'''
assert old2 in s2
s2 = s2.replace(old2, new2, 1)
open(p2, "w", encoding="utf-8").write(s2)
ast.parse(s2)
print("2. create route marks its publish pre-claimed")

# ---------- 2. dedup duplicate-key tolerance ----------
p3 = "src/core/event_dedup.py"
s3 = open(p3, encoding="utf-8").read()
old3 = '''            except Exception as e:
                logger.warning(f"Dedup DB mark failed — disabling DB dedup (memory-only): {e}")
                self._db_disabled = True'''
new3 = '''            except Exception as e:
                msg = str(e).lower()
                if "duplicate" in msg or "unique" in msg or "409" in msg:
                    # another worker inserted it first = already processed.
                    return False
                logger.warning(f"Dedup DB mark failed — disabling DB dedup (memory-only): {e}")
                self._db_disabled = True'''
assert old3 in s3
s3 = s3.replace(old3, new3, 1)
open(p3, "w", encoding="utf-8").write(s3)
ast.parse(s3)
print("3. dedup duplicate-key no longer disables DB dedup")

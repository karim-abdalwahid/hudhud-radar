import ast, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = "src/agent/scheduler.py"
src = open(p, encoding="utf-8").read()

old = '''        ids, errors = {}, {}
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
                errors["facebook"] = str(e)[:200]'''
new = '''        ids, errors = {}, {}
        media = (post.media_urls or [None])[0]
        if str(plat) in ("facebook", "both"):
            # FB publishing is fast and synchronous (one Graph call) — safe to
            # finish inside this tick. Uses the unified publisher path.
            try:
                from src.content_studio.models import ContentPlatform as _CP, PostType as _PT
                fb_res = await self.publisher.publish_content(
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
                errors["facebook"] = str(e)[:200]'''
assert old in src
src = src.replace(old, new, 1)
open(p, "w", encoding="utf-8").write(src)
ast.parse(src)
print("FB path now uses unified publish_content (tick stays short)")

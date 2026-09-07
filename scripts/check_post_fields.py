"""Inspect the normalized post fields produced by meta_feed_sync (read-only)."""
import json
import sys

sys.path.insert(0, ".")
from src.meta_api.feed_sync import meta_feed_sync  # noqa: E402

posts = meta_feed_sync.get_synced_posts(platform="all", limit=2)
if not posts:
    print("Cache empty")
else:
    p = posts[0]
    print("Post keys:", sorted(p.keys()))
    print("id present:", "id" in p or "post_id" in p)
    print("comments_count present:", "comments_count" in p)
    print("content_text len:", len(p.get("content_text") or ""))

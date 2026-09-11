"""Live check: fetch real IG media + views via the fixed feed_sync."""
import asyncio
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()

from src.meta_api.feed_sync import meta_feed_sync


async def main():
    items = await meta_feed_sync.fetch_instagram_media(limit=25)
    print(f"fetched {len(items)} IG media items")
    for it in items[:10]:
        print(f"  [{it['post_type']}] likes={it['likes_count']:<6} comments={it['comments_count']:<5} "
              f"views={it['views_count']:<8} {(it['content_text'] or '')[:40]!r}")
    reels = [i for i in items if i["post_type"] == "reel"]
    with_views = [i for i in reels if i["views_count"] > 0]
    print(f"\nreels: {len(reels)} | reels with real views: {len(with_views)}")


asyncio.run(main())

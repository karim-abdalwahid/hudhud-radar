"""WS-L: real publish loop — Threads publish -> CRM reflection -> delete."""
import asyncio, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()

from src.meta_api.extended_api import threads_publisher, threads_leads_sync


async def main():
    # 1. Publish a real test thread
    r = await threads_publisher.publish_thread(
        "🔧 رسالة اختبار تدقيق فني — سيتم حذفها تلقائيًا (Hudhud audit)", user_id=None)
    print("publish:", r)
    if r.get("status") != "success":
        return

    post_id = r.get("post_id") or (r.get("result") or {}).get("id") or (r.get("data") or {}).get("id")
    print("post_id:", post_id)

    # 2. Sync replies -> CRM bridge (the post has no replies yet, but the bridge must not crash)
    sync = await threads_leads_sync.sync_account_replies(limit_threads=5)
    print("sync-replies:", sync)

    # 3. Delete the test thread (cleanup)
    if post_id:
        d = await threads_publisher.delete_thread(post_id)
        print("delete:", d)

if __name__ == "__main__":
    asyncio.run(main())

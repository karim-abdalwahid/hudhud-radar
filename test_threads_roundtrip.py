"""LIVE round-trip proof for Threads: publish -> Graph verify -> delete -> confirm gone."""
import asyncio, json, os, sys, urllib.parse, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()
from src.meta_api.extended_api import threads_publisher

TEXT = "🧪 فحص Threads publish/delete (يُحذف خلال ثوانٍ)"


def tread(node):
    tok = threads_publisher._resolve_token(None)
    url = "https://graph.threads.net/v1.0/" + node + "?" + urllib.parse.urlencode({"fields": "id,text", "access_token": tok})
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {"http_error": e.code, "body": e.read().decode()[:120]}


async def main():
    pub = await threads_publisher.publish_thread(TEXT)
    print("1. publish:", pub)
    tid = pub.get("thread_id") or pub.get("post_id")
    live = tread(tid) if tid else {}
    print("2. live on Meta:", "id" in live, "| text:", str(live.get("text"))[:40])
    d = await threads_publisher.delete_thread(tid)
    print("3. delete:", d)
    after = tread(tid)
    gone = "id" not in after
    print("4. gone:", gone, "|", str(after)[:80])
    print("\nVERDICT THREADS:", "✅ REAL" if ("id" in live and gone) else "❌ CHECK")

asyncio.run(main())

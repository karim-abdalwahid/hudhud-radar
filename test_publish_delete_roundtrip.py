"""LIVE round-trip proof: publish real FB post via Studio -> verify on the Page
-> delete via app -> verify GONE on Meta (proving both features are REAL)."""
import json
import os
import sys
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()
from playwright.sync_api import sync_playwright

PAGE_ID = os.getenv("META_PAGE_ID")
TOKEN = os.getenv("META_PAGE_ACCESS_TOKEN")
G = "https://graph.facebook.com/v21.0"
TEST_TEXT = "🧪 فحص نظام Hudhud — منشور اختباري للحذف الفوري (نشر/حذف حقيقي)"


def page_feed_ids():
    url = f"{G}/{PAGE_ID}/posts?" + urllib.parse.urlencode(
        {"fields": "id,message,created_time", "limit": 10, "access_token": TOKEN})
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            return {p["id"]: (p.get("message") or "")[:40] for p in json.loads(r.read().decode()).get("data", [])}
    except Exception as e:
        print("feed read error:", e)
        return {}


with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_context().new_page()
    pg.goto("http://localhost:8000/login"); pg.wait_for_load_state("networkidle")
    pg.fill("#loginEmail", "admin.test@hudhud.test"); pg.fill("#loginPassword", "AdminTest#2026")
    pg.click("#loginBtn"); pg.wait_for_url("**/dashboard**", timeout=10000)

    print("1. creating post (publish_now) via the REAL Studio API...")
    r = pg.request.post("http://localhost:8000/api/content/posts", data={
        "platform": "facebook", "post_type": "post", "content_text": TEST_TEXT,
        "status": "publishing", "media_urls": [],
    })
    print("   create:", r.status, r.text()[:200])
    post = r.json()
    pid = post["id"]

    import time
    time.sleep(8)  # background publish task completes

    print("2. reading back the post status (meta ids)...")
    st = pg.request.get(f"http://localhost:8000/api/content/posts/{pid}")
    data = st.json()
    print("   status:", data.get("status"), "| meta_post_id:", data.get("meta_post_id"))

    meta = json.loads(data.get("meta_post_id") or "{}")
    fb_id = meta.get("facebook")
    ok1 = False
    if fb_id:
        ids = page_feed_ids()
        ok1 = any(fb_id in k or k in fb_id for k in ids)
        print(f"3. REAL page feed contains it? {ok1} (found {len(ids)} recent posts)")

    print("4. DELETING via the app...")
    d = pg.request.delete(f"http://localhost:8000/api/content/posts/{pid}")
    print("   delete:", d.status, d.text()[:220])

    time.sleep(3)
    ids2 = page_feed_ids()
    gone = fb_id not in "".join(ids2.keys()) if fb_id else True
    print(f"5. GONE from REAL page feed? {gone}")
    print("\nVERDICT:", "PUBLISH & DELETE ARE REAL ✅" if (ok1 and gone) else "CHECK ABOVE STEPS ⚠️")
    b.close()

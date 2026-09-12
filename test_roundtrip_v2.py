"""Round-trip v2: longer settle + direct Graph verification before delete."""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()
from playwright.sync_api import sync_playwright

TOKEN = os.getenv("META_PAGE_ACCESS_TOKEN")
G = "https://graph.facebook.com/v21.0"
TEST_TEXT = "🧪 فحص ثانٍ — إثبات النشر والحذف الحقيقيين (سيُحذف فورًا)"


def read_graph_object(obj_id):
    url = f"{G}/{obj_id}?" + urllib.parse.urlencode(
        {"fields": "id,message,status", "access_token": TOKEN})
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {"http_error": e.code}


with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_context().new_page()
    pg.goto("http://localhost:8000/login"); pg.wait_for_load_state("networkidle")
    pg.fill("#loginEmail", "admin.test@hudhud.test"); pg.fill("#loginPassword", "AdminTest#2026")
    pg.click("#loginBtn"); pg.wait_for_url("**/dashboard**", timeout=10000)

    r = pg.request.post("http://localhost:8000/api/content/posts", data={
        "platform": "facebook", "post_type": "post", "content_text": TEST_TEXT,
        "status": "publishing", "media_urls": []})
    pid = r.json()["id"]
    print("created:", pid)

    # poll until published (max 40s)
    meta = {}
    for _ in range(20):
        time.sleep(2)
        data = pg.request.get(f"http://localhost:8000/api/content/posts/{pid}").json()
        if data.get("status") == "published":
            meta = json.loads(data.get("meta_post_id") or "{}")
            print("PUBLISHED, meta ids:", meta, "| error_message:", data.get("error_message"))
            break
        if data.get("status") == "failed":
            print("FAILED:", data.get("error_message"))
            b.close(); sys.exit(1)
    fb_id = meta.get("facebook")

    # 2. direct Graph proof it exists on Meta
    live = read_graph_object(fb_id) if fb_id else {}
    exists = "id" in live
    print(f"2. object {fb_id} exists on REAL Meta? {exists} | graph status: {live.get('status')}")

    # 3. delete through the app
    d = pg.request.delete(f"http://localhost:8000/api/content/posts/{pid}")
    dd = d.json()
    print("3. app delete ->", dd.get("meta_deleted"), dd.get("meta_errors"))

    # 4. Graph confirms it's gone
    gone = read_graph_object(fb_id) if fb_id else {"id": None}
    is_gone = "id" not in gone
    print(f"4. object gone from Meta? {is_gone} (Graph says: {str(gone)[:90]})")
    print("\nVERDICT:", "PUBLISH+DELETE PROVEN REAL END-TO-END ✅" if (exists and is_gone) else "STILL SUSPECT ❌")
    b.close()

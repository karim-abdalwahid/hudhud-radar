"""Round-trip v3: Graph GET fields=id,message (valid combo) -> exists -> app delete -> gone."""
import json, os, sys, time, urllib.parse, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()
from playwright.sync_api import sync_playwright

TOKEN = os.getenv("META_PAGE_ACCESS_TOKEN")
G = "https://graph.facebook.com/v21.0"
TEST_TEXT = "🧪 فحص أخير — publish/delete إثبات حقيقي (يُحذف خلال ثوانٍ)"


def gread(obj_id):
    url = f"{G}/{obj_id}?" + urllib.parse.urlencode({"fields": "id,message", "access_token": TOKEN})
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {"http_error": e.code, "body": e.read().decode()[:120]}


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

    meta = {}
    for _ in range(25):
        time.sleep(2)
        d = pg.request.get(f"http://localhost:8000/api/content/posts/{pid}").json()
        if d.get("status") == "published":
            meta = json.loads(d.get("meta_post_id") or "{}"); break
        if d.get("status") == "failed":
            print("FAILED:", d.get("error_message")); b.close(); sys.exit(1)
    fb = meta.get("facebook")
    live = gread(fb)
    print("A. live on Meta:", "id" in live, "| message:", str(live.get("message"))[:40])
    dd = pg.request.delete(f"http://localhost:8000/api/content/posts/{pid}").json()
    print("B. app delete ->", dd.get("meta_deleted"), dd.get("meta_errors"))
    after = gread(fb)
    print("C. gone from Meta:", "id" not in after, "|", str(after)[:80])
    print("VERDICT:", "✅ PUBLISH + DELETE PROVEN REAL" if ("id" in live and "id" not in after) else "❌ RECHECK")
    b.close()

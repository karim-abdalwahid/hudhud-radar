"""LIVE round-trip: Instagram publish -> Graph verify -> app delete -> Graph confirm gone."""
import json, os, sys, time, urllib.parse, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()
from playwright.sync_api import sync_playwright

TOKEN = os.getenv("META_PAGE_ACCESS_TOKEN")
G = "https://graph.facebook.com/v21.0"
CAPTION = "🧪 فحص publish/delete حقيقي على Instagram — يُحذف خلال ثوانٍ"
IMG = "https://picsum.photos/id/237/720/720.jpg"


def gread(node, fields="id,permalink,media_product_type"):
    url = f"{G}/{node}?" + urllib.parse.urlencode({"fields": fields, "access_token": TOKEN})
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {"http_error": e.code, "body": e.read().decode()[:160]}


with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_context().new_page()
    pg.goto("http://localhost:8000/login"); pg.wait_for_load_state("networkidle")
    pg.fill("#loginEmail", "admin.test@hudhud.test"); pg.fill("#loginPassword", "AdminTest#2026")
    pg.click("#loginBtn"); pg.wait_for_url("**/dashboard**", timeout=10000)

    r = pg.request.post("http://localhost:8000/api/content/posts", data={
        "platform": "instagram", "post_type": "post", "content_text": CAPTION,
        "status": "publishing", "media_urls": [IMG]})
    pid = r.json()["id"]
    print("1. created:", pid)

    meta = {}
    err = None
    for _ in range(45):  # IG container flow needs time
        time.sleep(3)
        d = pg.request.get(f"http://localhost:8000/api/content/posts/{pid}").json()
        if d.get("status") == "published":
            meta = json.loads(d.get("meta_post_id") or "{}")
            print("2. PUBLISHED meta ids:", meta, "| error_message:", d.get("error_message"))
            break
        if d.get("status") in ("failed", "rejected_by_compliance"):
            err = d.get("error_message"); print("2. FAILED:", err); break
    ig_id = meta.get("instagram")
    if not ig_id:
        print("no IG id; aborting"); b.close(); sys.exit(1)

    live = gread(ig_id)
    print("3. on Meta now:", "id" in live, "| permalink:", str(live.get("permalink"))[:60])

    dd = pg.request.delete(f"http://localhost:8000/api/content/posts/{pid}").json()
    print("4. app delete:", dd.get("meta_deleted"), "| errors:", dd.get("meta_errors"))

    after = gread(ig_id)
    gone = "id" not in after
    print("5. gone from Meta:", gone, "|", str(after)[:100])
    print("\nVERDICT IG:", "✅ REAL" if ("id" in live and gone) else "❌ CHECK meta_errors")
    b.close()

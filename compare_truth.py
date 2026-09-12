"""Live truth-comparison: app analytics numbers vs REAL Graph API values."""
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

PAGE_ID = os.getenv("META_PAGE_ID", "")
IG_ID = os.getenv("META_INSTAGRAM_ACCOUNT_ID", "")
TOKEN = os.getenv("META_PAGE_ACCESS_TOKEN", "")
G = "https://graph.facebook.com/v21.0"
from src.core.supabase_client import supabase_db

# ---- what the DB holds (source of the dashboard) ----
rows = supabase_db.select("page_performance_metrics") or []
rows.sort(key=lambda r: (r.get("metric_date") or ""), reverse=True)
print(f"=== page_performance_metrics rows: {len(rows)} (last 6) ===")
for r in rows[:6]:
    print(f"  {r.get('metric_date')} [{r.get('platform')}] reach={r.get('reach')} "
          f"impr={r.get('impressions')} eng={r.get('engagement_rate')} fol={r.get('followers_count')}")

# ---- REAL values straight from Meta ----
def get(node, params):
    url = f"{G}/{node}?" + urllib.parse.urlencode({**params, "access_token": TOKEN})
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"error": str(e)[:150]}

print("\n=== REAL Facebook page ===")
real_f = get(PAGE_ID, {"fields": "fans_count,followers_count"})
print("page fans/followers:", {k: v for k, v in real_f.items() if k != "id"})
ins = get(f"{PAGE_ID}/insights", {"metric": "page_impressions,page_posts_impressions,page_fans_online_per_day"})
if "error" in ins:
    print("page insights ERROR:", ins["error"])
else:
    for m in ins.get("data", []):
        vals = m.get("values") or [{}]
        print(f"  {m.get('name')}: last={vals[-1].get('value')}")

print("\n=== REAL Instagram ===")
ig = get(IG_ID, {"fields": "followers_count,media_count"})
print("ig profile:", {k: v for k, v in ig.items() if k != "id"})
igi = get(f"{IG_ID}/insights", {"metric": "impressions,reach"})
print("ig account insights:", json.dumps(igi, ensure_ascii=False)[:250])

# ---- what the APP shows (live server, admin session) ----
print("\n=== /api/analytics/summary (as admin sees it) ===")
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_context().new_page()
    pg.goto("http://localhost:8000/login"); pg.wait_for_load_state("networkidle")
    pg.fill("#loginEmail", "admin.test@hudhud.test"); pg.fill("#loginPassword", "AdminTest#2026")
    pg.click("#loginBtn"); pg.wait_for_url("**/dashboard**", timeout=10000)
    s = pg.request.get("http://localhost:8000/api/analytics/summary").text()
    print("summary:", s[:700])
    b.close()

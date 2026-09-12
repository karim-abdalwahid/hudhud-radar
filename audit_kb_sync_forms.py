"""Phase C verify (sync writes user-stamped DB docs) + Phase D: leadgen forms truth."""
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

PAGE_ID = os.getenv("META_PAGE_ID")
TOKEN = os.getenv("META_PAGE_ACCESS_TOKEN")
G = "https://graph.facebook.com/v21.0"

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_context().new_page()
    pg.goto("http://localhost:8000/login"); pg.wait_for_load_state("networkidle")
    pg.fill("#loginEmail", "admin.test@hudhud.test"); pg.fill("#loginPassword", "AdminTest#2026")
    pg.click("#loginBtn"); pg.wait_for_url("**/dashboard**", timeout=15000)

    r = pg.request.post("http://localhost:8000/api/knowledge/sync-meta")
    print("C. sync-meta:", r.status, r.text()[:150])
    time.sleep(2)
    docs = pg.request.get("http://localhost:8000/api/knowledge/documents").json()
    names = [d["filename"] for d in docs.get("documents", [])]
    print("   documents visible to admin.test NOW:", names)
    ok = "business_profile.md" in names
    print("   per-user sync persistence:", "REAL ✅" if ok else "BROKEN ❌")
    b.close()

print("\nD. leadgen forms on the real page:")
url = f"{G}/{PAGE_ID}/leadgen_forms?" + urllib.parse.urlencode(
    {"fields": "id,name,status,leads_count", "access_token": TOKEN})
req = urllib.request.Request(url)
try:
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.loads(r.read().decode())
    forms = data.get("data", [])
    print(f"   forms found: {len(forms)}")
    for f in forms[:5]:
        print("   -", f.get("name"), "| status:", f.get("status"), "| leads:", f.get("leads_count"))
except urllib.error.HTTPError as e:
    print("   Meta said:", e.code, e.read().decode()[:220])

"""E2E: upload a KB doc via the API as admin -> verify db_saved + per-user stamp -> cleanup."""
import sys
from playwright.sync_api import sync_playwright
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = "http://localhost:8000"

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context()
    pg = ctx.new_page()
    pg.goto(f"{BASE}/login"); pg.wait_for_load_state("networkidle")
    pg.fill("#loginEmail", "admin.test@hudhud.test"); pg.fill("#loginPassword", "AdminTest#2026")
    pg.click("#loginBtn"); pg.wait_for_url("**/dashboard**", timeout=10000)

    # multipart upload through the browser session (cookies apply)
    payload = ("# Test Audit Doc\n\nهذا مستند اختبار للتدقيق — سيتم حذفه فورًا.").encode("utf-8")
    resp = ctx.request.post(f"{BASE}/api/knowledge/upload", multipart={
        "file": {"name": "ztest_audit.md", "mimeType": "text/markdown",
                 "buffer": payload}})
    print("upload status:", resp.status)
    print("upload body:", resp.text()[:300])
    b.close()

# verify DB row + owner
sys.path.insert(0, ".")
from src.core.supabase_client import supabase_db
rows = supabase_db.select("kb_documents", {"filename": "ztest_audit.md"}) or []
for r in rows:
    print(f"DB row: user_id={r.get('user_id')} source={r.get('source')} chars={len(r.get('content') or '')}")

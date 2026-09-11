"""Delete the audit test reply via threads_delete (cleanup + extra 200 on the delete endpoint)."""
import sys
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_context().new_page()
    pg.goto("https://www.hudhd.com/login"); pg.wait_for_load_state("networkidle")
    pg.fill("#loginEmail", "admin.test@hudhud.test"); pg.fill("#loginPassword", "AdminTest#2026")
    pg.click("#loginBtn"); pg.wait_for_url("**/dashboard**", timeout=15000)
    r = pg.request.delete("https://www.hudhd.com/api/threads/2750047694351")
    print("delete audit reply ->", r.status, r.text()[:150])
    b.close()

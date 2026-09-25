import sys
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_context(viewport={"width": 1920, "height": 1080}).new_page()
    pg.goto("http://localhost:8000/login"); pg.wait_for_load_state("networkidle")
    pg.fill("#loginEmail", "admin.test@hudhud.test"); pg.fill("#loginPassword", "AdminTest#2026")
    pg.click("#loginBtn"); pg.wait_for_url("**/dashboard**", timeout=10000)
    r = pg.request.get("http://localhost:8000/api/threads/my-posts?limit=3")
    print("HTTP:", r.status)
    print("body:", r.text()[:400])
    b.close()

"""Perform the threads_manage_replies WRITE test call ON PRODUCTION
(with the real OAuth token resolved server-side)."""
import sys
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_context().new_page()
    pg.goto("https://www.hudhd.com/login"); pg.wait_for_load_state("networkidle")
    pg.fill("#loginEmail", "admin.test@hudhud.test")
    pg.fill("#loginPassword", "AdminTest#2026")
    pg.click("#loginBtn"); pg.wait_for_url("**/dashboard**", timeout=15000)

    THREAD_ID = "18116660710767178"  # the coffee-pricing thread
    r = pg.request.post(
        "https://www.hudhd.com/api/threads/" + THREAD_ID + "/reply",
        data={"text": "شكراً لتواصلكم! فريق Hudhud 🧡"})
    print("POST reply on production ->", r.status)
    print("body:", r.text()[:300])
    b.close()

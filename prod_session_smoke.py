import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_context().new_page()
    pg.goto("https://www.hudhd.com/login"); pg.wait_for_load_state("networkidle")
    pg.fill("#loginEmail", "admin.test@hudhud.test"); pg.fill("#loginPassword", "AdminTest#2026")
    pg.click("#loginBtn"); pg.wait_for_url("**/dashboard**", timeout=20000)
    for ep in ["/api/meta/status", "/api/connections", "/api/automations", "/api/ai/pause", "/api/admin/overview"]:
        r = pg.request.get("https://www.hudhd.com" + ep)
        print(f"{ep:<24} {r.status}")
    # pause echo on prod (restore immediately)
    r = pg.request.post("https://www.hudhd.com/api/ai/pause", data={"paused": True})
    s = r.json()
    r2 = pg.request.post("https://www.hudhd.com/api/ai/pause", data={"paused": False})
    print("pause on/off prod echo:", s.get("global_paused"), "->", r2.json().get("global_paused"))
    b.close()

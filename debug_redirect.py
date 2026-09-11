"""Debug: why doesn't client-mode redirect fire on /users?"""
import sys
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = "http://localhost:8000"

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_context(viewport={"width": 1920, "height": 1080}).new_page()
    pg.on("pageerror", lambda e: print("[pageerror]", str(e)[:200]))
    pg.on("console", lambda m: print(f"[{m.type}]", m.text[:200]) if m.type == "error" else None)

    pg.goto(f"{BASE}/login"); pg.wait_for_load_state("networkidle")
    pg.fill("#loginEmail", "admin.test@hudhud.test"); pg.fill("#loginPassword", "AdminTest#2026")
    pg.click("#loginBtn"); pg.wait_for_url("**/dashboard**", timeout=10000)
    pg.wait_for_timeout(2000)

    me = pg.evaluate("async () => await (await fetch('/auth/me')).json()")
    print("/auth/me on dashboard:", me)

    pg.evaluate("localStorage.setItem('hudhud_role_mode', 'client')")
    pg.goto(f"{BASE}/users")
    pg.wait_for_timeout(4000)
    state = pg.evaluate("""() => ({
        url: location.href,
        isAdmin: hudhudRoleManager._isAdmin,
        saved: localStorage.getItem('hudhud_role_mode'),
        isDevRoute: hudhudRoleManager.isDevRoute(),
        body: document.body.className
    })""")
    print("state on /users:", state)
    b.close()
print("DONE")

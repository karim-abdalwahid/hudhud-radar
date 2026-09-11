"""Debug: test /auth/me FROM INSIDE the /users page."""
import sys
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = "http://localhost:8000"

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_context(viewport={"width": 1920, "height": 1080}).new_page()
    pg.on("pageerror", lambda e: print("[pageerror]", str(e)[:300]))
    pg.on("console", lambda m: print(f"[{m.type}]", m.text[:300]) if m.type == "error" else None)
    pg.on("requestfailed", lambda r: print("[requestfailed]", r.url[:100], r.failure))

    pg.goto(f"{BASE}/login"); pg.wait_for_load_state("networkidle")
    pg.fill("#loginEmail", "admin.test@hudhud.test"); pg.fill("#loginPassword", "AdminTest#2026")
    pg.click("#loginBtn"); pg.wait_for_url("**/dashboard**", timeout=10000)
    pg.evaluate("localStorage.setItem('hudhud_role_mode', 'client')")

    print("=== navigating to /users ===")
    pg.goto(f"{BASE}/users")
    pg.wait_for_load_state("networkidle")
    pg.wait_for_timeout(3000)

    result = pg.evaluate("""async () => {
        const out = {};
        try {
            const r = await fetch('/auth/me');
            out.status = r.status;
            out.redirected = r.redirected;
            out.finalUrl = r.url;
            const text = await r.text();
            out.body = text.slice(0, 200);
        } catch (e) { out.error = String(e); }
        out.cookiePresent = document.cookie.includes('hudhud_session');
        out.isAdmin = hudhudRoleManager._isAdmin;
        return out;
    }""")
    for k, v in result.items():
        print(f"  {k}: {v}")
    b.close()
print("DONE")

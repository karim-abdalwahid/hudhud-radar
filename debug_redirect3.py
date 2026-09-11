"""Catch init() exception live on /users."""
import sys
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = "http://localhost:8000"

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_context(viewport={"width": 1920, "height": 1080}).new_page()
    pg.on("pageerror", lambda e: print("[pageerror]", str(e)[:300]))
    pg.on("console", lambda m: print(f"[{m.type}]", m.text[:250]) if m.type in ("error", "warning") else None)

    pg.goto(f"{BASE}/login"); pg.wait_for_load_state("networkidle")
    pg.fill("#loginEmail", "admin.test@hudhud.test"); pg.fill("#loginPassword", "AdminTest#2026")
    pg.click("#loginBtn"); pg.wait_for_url("**/dashboard**", timeout=10000)
    pg.evaluate("localStorage.setItem('hudhud_role_mode', 'client')")
    pg.goto(f"{BASE}/users")
    pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(2500)

    result = pg.evaluate("""async () => {
        const out = {url: location.href};
        out.isAdminBefore = hudhudRoleManager._isAdmin;
        try {
            await hudhudRoleManager.init();
            out.reinit = 'completed';
        } catch (e) {
            out.reinit = 'THREW: ' + (e && e.stack ? e.stack.split('\\n').slice(0,3).join(' | ') : String(e));
        }
        out.isAdminAfter = hudhudRoleManager._isAdmin;
        out.urlAfter = location.href;
        return out;
    }""")
    for k, v in result.items():
        print(f"  {k}: {v}")
    b.close()
print("DONE")

"""Instrument fetch inside the page to see exactly what init's /auth/me gets."""
import sys
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = "http://localhost:8000"

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_context(viewport={"width": 1920, "height": 1080}).new_page()
    pg.on("pageerror", lambda e: print("[pageerror]", str(e)[:300]))

    pg.goto(f"{BASE}/login"); pg.wait_for_load_state("networkidle")
    pg.fill("#loginEmail", "admin.test@hudhud.test"); pg.fill("#loginPassword", "AdminTest#2026")
    pg.click("#loginBtn"); pg.wait_for_url("**/dashboard**", timeout=10000)
    pg.evaluate("localStorage.setItem('hudhud_role_mode', 'client')")

    # Intercept fetch BEFORE navigating to /users
    pg.evaluate("""() => {
        window.__fetchLog = [];
        const orig = window.fetch;
        window.fetch = function(...args) {
            const url = String(args[0]);
            const p = orig.apply(this, args);
            if (url.includes('/auth/me')) {
                p.then(r => window.__fetchLog.push({url, status: r.status, ok: r.ok}))
                 .catch(e => window.__fetchLog.push({url, error: String(e)}));
            }
            return p;
        };
    }""")

    pg.goto(f"{BASE}/users")
    pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(3000)

    out = pg.evaluate("""() => ({
        log: window.__fetchLog || 'NOT CAPTURED (page navigated away - fresh page)',
        isAdmin: hudhudRoleManager._isAdmin,
        url: location.href
    })""")
    print("fetch log:", out["log"])
    print("isAdmin:", out["isAdmin"], "| url:", out["url"])

    # If the log was lost due to navigation, try re-running init with live interception
    live = pg.evaluate("""async () => {
        window.__live = [];
        const orig = window.fetch;
        window.fetch = function(...args) {
            const url = String(args[0]);
            const p = orig.apply(this, args);
            if (url.includes('/auth/me')) {
                p.then(r => window.__live.push({url, status: r.status}))
                 .catch(e => window.__live.push({url, error: String(e)}));
            }
            return p;
        };
        localStorage.setItem('hudhud_role_mode', 'client');
        await hudhudRoleManager.init();
        return {log: window.__live, isAdmin: hudhudRoleManager._isAdmin, url: location.href};
    }""")
    print("live re-init:", live)
    b.close()
print("DONE")

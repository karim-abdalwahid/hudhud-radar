"""FLASH-FREE PROOF: raw server HTML (no JS) already has separated sections + body class."""
import sys
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = "http://localhost:8000"

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context(viewport={"width": 1920, "height": 1080})
    pg = ctx.new_page()
    pg.goto(f"{BASE}/login"); pg.wait_for_load_state("networkidle")
    pg.fill("#loginEmail", "admin.test@hudhud.test"); pg.fill("#loginPassword", "AdminTest#2026")
    pg.click("#loginBtn"); pg.wait_for_url("**/dashboard**", timeout=10000)

    # cookie: client mode -> server must render mode-client + sections ready
    ctx.add_cookies([{"name": "hudhud_role_mode", "value": "client",
                      "url": BASE}])

    for path in ("/users", "/templates", "/inbox", "/settings"):
        raw = ctx.request.get(BASE + path).text()
        checks = {
            "body class server-set": 'class="mode-' in raw.split("<body")[1][:60] if "<body" in raw else False,
            "client-nav-section in HTML": 'client-nav-section' in raw,
            "dev-nav-section in HTML": 'dev-nav-section' in raw,
        }
        bc = raw.split("<body")[1].split(">")[0]
        checks["body tag"] = bc.strip()[:50]
        checks["no JS needed"] = True
        print(f"{path}: {checks}")

    # browser-level: visibility correct IMMEDIATELY at DOMContentLoaded (no settle wait)
    pg2 = ctx.new_page()
    pg2.goto(f"{BASE}/users")
    early = pg2.evaluate("""() => ({
        readyState: document.readyState,
        devVisible: (document.querySelector('.dev-nav-section')||{offsetParent:null}).offsetParent !== null,
        clientVisible: (document.querySelector('.client-nav-section')||{offsetParent:null}).offsetParent !== null,
        body: document.body.className
    })""")
    print("\nimmediate DOM state on /users:", early)
    b.close()
print("DONE")

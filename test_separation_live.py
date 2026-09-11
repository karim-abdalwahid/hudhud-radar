"""Verify two-way role separation + /users & /templates fixes (live)."""
import sys
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = "http://localhost:8000"
EMAIL, PASSWORD = "admin.test@hudhud.test", "AdminTest#2026"

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context(viewport={"width": 1920, "height": 1080})
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)[:150]))

    pg.goto(f"{BASE}/login"); pg.wait_for_load_state("networkidle")
    pg.fill("#loginEmail", EMAIL); pg.fill("#loginPassword", PASSWORD)
    pg.click("#loginBtn"); pg.wait_for_url("**/dashboard**", timeout=10000)
    pg.wait_for_timeout(2500)

    # --- Test 1: admin defaults to developer mode on dashboard? saved mode governs.
    # Force client mode, then try to open /users directly -> expect redirect to /dashboard
    pg.evaluate("localStorage.setItem('hudhud_role_mode', 'client')")
    pg.goto(f"{BASE}/users")
    pg.wait_for_timeout(2500)
    print("1) client mode + /users  ->", pg.url, "(expect redirect to /dashboard)")

    # --- Test 2: client mode on /inbox: dev links hidden? users/templates links hidden?
    pg.goto(f"{BASE}/inbox")
    pg.wait_for_timeout(2500)
    vis = pg.evaluate("""() => {
        const links = [...document.querySelectorAll('.sidebar-nav a.nav-item')].map(a => a.getAttribute('href'));
        const devSection = document.querySelector('.dev-nav-section');
        const devVisible = devSection && devSection.offsetParent !== null;
        return {links, devVisible, body: document.body.className};
    }""")
    print("2) client mode nav links:", vis["links"])
    print("   dev section visible?", vis["devVisible"], "| body:", vis["body"])

    # --- Test 3: switch to developer mode -> client sections hidden, admin links visible
    pg.evaluate("hudhudRoleManager.setMode('developer')")
    pg.wait_for_timeout(1200)
    dev = pg.evaluate("""() => {
        const client = document.querySelector('.client-nav-section');
        const devSection = document.querySelector('.dev-nav-section');
        return {
            clientVisible: client ? client.offsetParent !== null : 'no-wrapper',
            devLinks: devSection ? [...devSection.querySelectorAll('a')].map(a => a.getAttribute('href')) : [],
            body: document.body.className
        };
    }""")
    print("3) developer mode: client nav visible?", dev["clientVisible"],
          "| dev links:", dev["devLinks"], "| body:", dev["body"])

    # --- Test 4: /users page in developer mode — saas.css linked (styled switcher)?
    pg.goto(f"{BASE}/users")
    pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(2000)
    users = pg.evaluate("""() => {
        const sw = document.querySelector('.role-mode-switcher');
        const css = sw ? getComputedStyle(sw).borderRadius : 'none';
        const cssLinked = !![...document.styleSheets].some(s => (s.href||'').includes('saas.css'));
        const chips = document.querySelectorAll('#role-chips .chip').length;
        const pager = document.getElementById('pager') ? 'present' : 'missing';
        return {cssLinked, switcherRadius: css, filterChips: chips, pager};
    }""")
    print("4) /users: saas.css linked?", users["cssLinked"],
          "| switcher styled (radius):", users["switcherRadius"],
          "| filter chips:", users["filterChips"], "| pager:", users["pager"])

    # --- Test 5: /templates page styled too
    pg.goto(f"{BASE}/templates")
    pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(1500)
    tpl = pg.evaluate("""() => ({
        cssLinked: !![...document.styleSheets].some(s => (s.href||'').includes('saas.css')),
        sidebar: !!document.querySelector('.app-sidebar')
    })""")
    print("5) /templates: saas.css linked?", tpl["cssLinked"], "| sidebar:", tpl["sidebar"])

    print("pageerrors:", len(errors))
    for e in errors[:5]: print("  ", e)
    b.close()
print("DONE")

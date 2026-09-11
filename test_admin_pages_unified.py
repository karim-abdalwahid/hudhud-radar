"""Verify /users + /templates now use the unified chrome (styles computed match the app)."""
import sys
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = "http://localhost:8000"

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_context(viewport={"width": 1920, "height": 1080}).new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)[:150]))

    pg.goto(f"{BASE}/login"); pg.wait_for_load_state("networkidle")
    pg.fill("#loginEmail", "admin.test@hudhud.test"); pg.fill("#loginPassword", "AdminTest#2026")
    pg.click("#loginBtn"); pg.wait_for_url("**/dashboard**", timeout=10000)

    for path in ("/users", "/templates"):
        pg.goto(f"{BASE}{path}")
        pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(2500)
        checks = pg.evaluate("""() => {
            const sidebar = document.querySelector('.app-sidebar');
            const layout = document.querySelector('.app-layout');
            const main = document.querySelector('.app-main');
            const topbar = document.querySelector('.app-topbar');
            const css = [...document.styleSheets].some(s => (s.href||'').includes('saas.css'));
            const sw = document.querySelector('.role-mode-switcher');
            const sidebarBg = sidebar ? getComputedStyle(sidebar).backgroundColor : 'n/a';
            const bodyFont = getComputedStyle(document.body).fontFamily.slice(0, 30);
            const navLinks = [...document.querySelectorAll('.sidebar-nav a.nav-item')].map(a => a.getAttribute('href'));
            const devSection = document.querySelector('.dev-nav-section');
            const clientSection = document.querySelector('.client-nav-section');
            return {
                layout, sidebar, main, topbar, css, switcher: !!sw, sidebarBg, bodyFont, navLinks,
                devVisible: devSection ? devSection.offsetParent !== null : false,
                clientVisible: clientSection ? clientSection.offsetParent !== null : false,
                bodyClass: document.body.className,
                metaPill: !!document.getElementById('meta-status-container')
            };
        }""")
        print(f"\n===== {path} =====")
        print(" shared chrome (layout/sidebar/main/topbar):",
              all(checks[k] for k in ("layout", "sidebar", "main", "topbar")))
        print(" saas.css linked:", checks["css"], "| role switcher:", checks["switcher"],
              "| meta pill:", checks["metaPill"])
        print(" sidebar bg:", checks["sidebarBg"], "| font:", checks["bodyFont"])
        print(" mode:", checks["bodyClass"], "| dev section visible:", checks["devVisible"],
              "| client section visible:", checks["clientVisible"])
        print(" nav links:", checks["navLinks"])
        print(" page errors:", errs[-2:] if errs else "none")

    # functional check: users table still renders + search present
    pg.goto(f"{BASE}/users"); pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(2500)
    fn = pg.evaluate("""() => ({
        rows: document.querySelectorAll('#users-body tr').length,
        chips: document.querySelectorAll('#role-chips .chip').length,
        kpis: [...document.querySelectorAll('[id^=kpi-]')].map(e => e.textContent.trim()).slice(0,3)
    })""")
    print("\n/users functional:", fn)
    b.close()
print("DONE")

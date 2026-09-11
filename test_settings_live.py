"""Live test: /settings — capture JS errors + check whether tabs actually initialize."""
import sys
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = "http://localhost:8000"

errors = []
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_context(viewport={"width": 1920, "height": 1080}).new_page()
    pg.on("pageerror", lambda e: errors.append(f"[pageerror] {str(e)[:300]}"))
    pg.on("console", lambda m: errors.append(f"[console.{m.type}] {m.text[:300]}") if m.type == "error" else None)

    pg.goto(f"{BASE}/login"); pg.wait_for_load_state("networkidle")
    pg.fill("#loginEmail", "admin.test@hudhud.test")
    pg.fill("#loginPassword", "AdminTest#2026")
    pg.click("#loginBtn")
    pg.wait_for_url("**/dashboard**", timeout=10000)

    pg.goto(f"{BASE}/settings")
    pg.wait_for_load_state("networkidle")
    pg.wait_for_timeout(3500)

    vis = pg.evaluate("""() => {
        const out = {tabs: [], visibleSections: 0};
        ['meta','threads','ai','webhooks','security'].forEach(t => {
            const el = document.getElementById('set-tab-page-' + t);
            out.tabs.push(t + '=' + (el ? getComputedStyle(el).display : 'missing'));
        });
        document.querySelectorAll('.panel-section').forEach(s => {
            if (s.offsetParent !== null) out.visibleSections++;
        });
        const sw = document.querySelector('.role-mode-switcher');
        out.roleSwitcher = sw ? 'present' : 'absent';
        const devSection = document.querySelector('.dev-nav-section');
        out.devNavDisplay = devSection ? getComputedStyle(devSection).display : 'none';
        out.bodyClass = document.body.className;
        return out;
    }""")
    print("visible tab pages:", vis["tabs"])
    print("visible panel-sections:", vis["visibleSections"])
    print("role switcher:", vis["roleSwitcher"], "| dev nav display:", vis["devNavDisplay"])
    print("body class:", vis["bodyClass"])
    print("\nJS errors captured:", len(errors))
    for e in errors[:10]:
        print("  ", e)
    b.close()
print("DONE")

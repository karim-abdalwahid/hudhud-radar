"""Verify: create post deep-link opens publisher pane + topbar not glued."""
import sys
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = "http://localhost:8000"

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_context(viewport={"width": 1920, "height": 1080}).new_page()

    pg.goto(f"{BASE}/login"); pg.wait_for_load_state("networkidle")
    pg.fill("#loginEmail", "admin.test@hudhud.test"); pg.fill("#loginPassword", "AdminTest#2026")
    pg.click("#loginBtn"); pg.wait_for_url("**/dashboard**", timeout=10000)

    # 1. overview topbar: create post link target + not glued to breadcrumb
    pg.goto(f"{BASE}/dashboard"); pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(1500)
    link = pg.evaluate("""() => {
        const a = document.querySelector('.topbar-actions a[href*="studio"]');
        const acts = document.querySelector('.topbar-actions');
        const crumb = document.querySelector('.topbar-breadcrumb');
        const ar = acts.getBoundingClientRect();
        const cr = crumb.getBoundingClientRect();
        return {href: a ? a.getAttribute('href') : null,
                actsStyle: acts.getAttribute('style'),
                gapBetween: Math.round(ar.left - cr.right)};
    }""")
    print("create post href:", link["href"])
    print("actions style:", link["actsStyle"])
    print("gap between breadcrumb and actions (px):", link["gapBetween"])

    # 2. follow the link -> publisher pane active?
    pg.click('.topbar-actions a[href*="studio"]')
    pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(1500)
    pane = pg.evaluate("""() => {
        const pub = document.getElementById('studio-pane-publisher');
        const feed = document.getElementById('studio-pane-feed');
        const ai = document.getElementById('studio-pane-ai');
        const vis = el => el && getComputedStyle(el).display !== 'none';
        return {publisherVisible: vis(pub), feedVisible: vis(feed), aiVisible: vis(ai),
                activeBtn: (document.querySelector('.studio-tab-bar .active')||{textContent:''}).textContent.trim().slice(0,30)};
    }""")
    print("\nafter clicking Create Post:", pane)
    b.close()
print("DONE")

import sys
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_context(viewport={"width": 1920, "height": 1080}).new_page()
    pg.goto("http://localhost:8000/login"); pg.wait_for_load_state("networkidle")
    pg.fill("#loginEmail", "admin.test@hudhud.test"); pg.fill("#loginPassword", "AdminTest#2026")
    pg.click("#loginBtn"); pg.wait_for_url("**/dashboard**", timeout=10000)
    pg.goto("http://localhost:8000/studio?view=publisher")
    pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(2000)
    r = pg.evaluate("""() => ({
        threadsOption: !!document.querySelector('#post-platform option[value=threads]'),
        threadsSection: !!document.getElementById('threads-text'),
        publishBtn: !!document.querySelector('button[onclick*="publishToThreads"]'),
        refreshBtn: !!document.querySelector('button[onclick*="loadMyThreads"]')
    })""")
    print("studio threads UI:", r)
    posts = pg.evaluate("""async () => await (await fetch('/api/threads/my-posts?limit=5')).json()""")
    print("my-posts API:", {"status": posts.get("status"), "count": len(posts.get("posts", []))})
    b.close()

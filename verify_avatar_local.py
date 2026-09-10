"""Verify avatar rendering END-TO-END on the LOCAL server (new code)."""
import sys
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "http://localhost:8000"
EMAIL = "admin.test@hudhd.test"
PASSWORD = "AdminTest#2026"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_context(viewport={"width": 1920, "height": 1080}).new_page()

    page.goto(f"{BASE}/login")
    page.wait_for_load_state("networkidle")
    page.fill("#loginEmail", EMAIL)
    page.fill("#loginPassword", PASSWORD)
    page.click("#loginBtn")
    page.wait_for_url("**/dashboard**", timeout=10000)

    page.goto(f"{BASE}/inbox")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(4000)

    # Open the first conversation to render chat header + dossier
    cards = page.query_selector_all(".conv-card")
    print(f"conversation cards rendered: {len(cards)}")
    if cards:
        cards[0].click()
        page.wait_for_timeout(2000)

    # Inspect all avatar spots
    result = page.evaluate("""() => {
        const out = {};
        // 1. conversation list avatars
        out.list_avatars = [...document.querySelectorAll('.conv-card .conv-avatar img')].map(i => i.src.slice(0, 60));
        // 2. active chat header avatar
        const header = document.getElementById('active-chat-avatar');
        out.header_img = header ? (header.querySelector('img') ? header.querySelector('img').src.slice(0, 60) : 'NO IMG -> text: ' + header.textContent) : 'no element';
        // 3. dossier avatar
        const dossier = document.getElementById('lead-panel-avatar');
        out.dossier_img = dossier ? (dossier.querySelector('img') ? dossier.querySelector('img').src.slice(0, 60) : 'NO IMG -> html: ' + dossier.innerHTML.slice(0, 40)) : 'no element';
        out.dossier_name = document.getElementById('lead-panel-name')?.textContent;
        // 4. did the API deliver avatar?
        out.api_avatar_key = typeof window.__convs !== 'undefined';
        return out;
    }""")
    for k, v in result.items():
        print(f"  {k}: {v}")

    # Check the raw API response delivered to the page
    api = page.evaluate("""async () => {
        const r = await fetch('/api/inbox/conversations');
        const j = await r.json();
        return j.conversations.map(c => ({name: c.name, avatar: c.avatar ? c.avatar.slice(0, 60) : null, channel: c.channel}));
    }""")
    print("API conversations:", api)

    browser.close()
print("DONE")

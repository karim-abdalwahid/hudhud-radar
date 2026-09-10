"""Check what the /inbox UI ACTUALLY renders (DOM ground truth) + JS console errors."""
import os
import sys
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "https://www.hudhd.com"
EMAIL = "admin.test@hudhd.test"
PASSWORD = "AdminTest#2026"

console_errors = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1920, "height": 1080})
    page = ctx.new_page()
    page.on("console", lambda m: console_errors.append(f"[{m.type}] {m.text[:200]}") if m.type in ("error", "warning") else None)
    page.on("pageerror", lambda e: console_errors.append(f"[pageerror] {str(e)[:300]}"))

    page.goto(f"{BASE}/login", timeout=30000)
    page.wait_for_load_state("networkidle")
    page.fill("#loginEmail", EMAIL)
    page.fill("#loginPassword", PASSWORD)
    page.click("#loginBtn")
    page.wait_for_url("**/dashboard**", timeout=10000)

    page.goto(f"{BASE}/inbox", timeout=30000)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(5000)

    # Count common thread/conversation UI elements
    stats = page.evaluate("""() => {
        const q = (sel) => document.querySelectorAll(sel).length;
        return {
            totalElements: document.querySelectorAll('*').length,
            possibleThreadItems: q('[class*=conversation], [class*=thread], [class*=chat-item], [class*=conv-item]'),
            possibleMessageBubbles: q('[class*=message], [class*=bubble]'),
            bodyTextLength: document.body.innerText.length,
            emptyStateVisible: !!document.querySelector('[class*=empty], [class*=no-data]'),
        };
    }""")
    print("DOM stats:", stats)

    # Extract visible text of the conversations sidebar area
    visible_text = page.evaluate("""() => {
        // grab text of the main app container
        const main = document.querySelector('#root, #app, main, body');
        return main ? main.innerText : '';
    }""")
    print("\n===== VISIBLE PAGE TEXT (first 2000 chars) =====")
    print(visible_text[:2000])

    print("\n===== JS CONSOLE ERRORS/WARNINGS =====")
    if console_errors:
        for e in console_errors[:20]:
            print(" ", e)
    else:
        print("  (none)")

    browser.close()
print("\nDONE")

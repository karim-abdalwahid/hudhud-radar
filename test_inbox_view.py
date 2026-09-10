"""Login to PRODUCTION hudhd.com as test admin, open /inbox, screenshot + capture API."""
import os
import sys
import json
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = r"C:\Users\Dell\AppData\Local\Temp\opencode"
os.makedirs(OUT, exist_ok=True)

BASE = "https://www.hudhd.com"
EMAIL = "admin.test@hudhd.test"
PASSWORD = "AdminTest#2026"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1920, "height": 1080})
    page = ctx.new_page()

    api_responses = {}
    def on_response(resp):
        if "/api/inbox" in resp.url or "/api/analytics" in resp.url or "/api/notifications" in resp.url:
            try:
                api_responses[resp.url] = {"status": resp.status, "body": resp.text()[:1500]}
            except Exception:
                pass
    page.on("response", on_response)

    print("1. Opening login page...")
    page.goto(f"{BASE}/login", timeout=30000)
    page.wait_for_load_state("networkidle")

    print("2. Logging in...")
    page.fill("#loginEmail", EMAIL)
    page.fill("#loginPassword", PASSWORD)
    page.click("#loginBtn")
    try:
        page.wait_for_url("**/dashboard**", timeout=10000)
        print(f"   -> Logged in, landed on: {page.url}")
    except Exception:
        print(f"   -> LOGIN FAILED or no redirect. URL: {page.url}")
        err = page.inner_text("body")[:300]
        print(f"   Body snippet: {err}")
        browser.close()
        sys.exit(1)

    print("3. Opening /inbox...")
    page.goto(f"{BASE}/inbox", timeout=30000)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(4000)

    page.screenshot(path=os.path.join(OUT, "inbox_production.png"), full_page=False)
    print(f"   Screenshot saved: {os.path.join(OUT, 'inbox_production.png')}")

    print("\n4. Captured API responses:")
    for url, info in api_responses.items():
        print(f"   [{info['status']}] {url.split('hudhd.com')[-1]}")
        body = info.get("body", "")
        try:
            j = json.loads(body)
            if "conversations" in j:
                convs = j["conversations"]
                print(f"      conversations count = {len(convs)}")
                for c in convs[:5]:
                    print(f"      - name={c.get('name')} channel={c.get('channel')} msgs={len(c.get('messages', []))}")
        except Exception:
            print(f"      body: {body[:200]}")

    browser.close()
print("\nDONE")

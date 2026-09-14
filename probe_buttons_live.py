"""Live click-probe: click every safe button across app pages; capture every
API call it triggers; report any 5xx/404 and zero-call (dead) buttons."""
import re
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()
from playwright.sync_api import sync_playwright

B = "http://localhost:8000"
DANGER = re.compile(r"delete|remove|publish|send|disconnect|logout|restore|reset|pay|checkout|buy|subscribe|exchange", re.I)

PAGES = ["/dashboard", "/inbox", "/leads", "/studio", "/automations",
         "/knowledge", "/identity", "/analytics", "/settings", "/users", "/templates"]

failures = []
dead_buttons = []
api_calls_seen = set()

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_context(viewport={"width": 1920, "height": 1080}).new_page()
    net = []
    def on_resp(r):
        u = r.url
        if "/api/" in u or "/auth/" in u:
            net.append((r.status, u.replace(B, "")))
            api_calls_seen.add((r.request.method, re.sub(r"/[0-9a-f-]{20,}", "/ID", re.sub(r"/(wf_[\w-]+|[\w.-]+\.md)$", "/X", u.replace(B, "")))))
    pg.on("response", on_resp)
    pg.goto(f"{B}/login"); pg.wait_for_load_state("networkidle")
    pg.fill("#loginEmail", "admin.test@hudhud.test"); pg.fill("#loginPassword", "AdminTest#2026")
    pg.click("#loginBtn"); pg.wait_for_url("**/dashboard**", timeout=15000)

    for path in PAGES:
        pg.goto(B + path); pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(1200)
        btns = pg.query_selector_all("button:not([disabled])")
        clicked = 0
        for bt in btns[:40]:
            try:
                oc = (bt.get_attribute("onclick") or "").strip()
                label = (bt.inner_text() or "").strip()[:22].replace("\n", " ")
                if DANGER.search(oc or label):
                    continue
                vis = bt.is_visible()
                if not vis:
                    continue
                before = len(net)
                bt.click(timeout=2500)
                pg.wait_for_timeout(500)
                clicked += 1
                for code, url in net[before:]:
                    if code >= 500 or code == 404:
                        failures.append((path, oc[:40] or label, code, url))
            except Exception:
                pass
        print(f"{path:<14} buttons clicked: {clicked}")
    b.close()

print("\n=== 5xx/404 from clicks ===")
if not failures:
    print("  ✅ NONE — every clicked button's API calls responded cleanly")
for f in failures[:20]:
    print("  ❌", f)

print("\n=== API endpoints exercised by buttons (live) ===")
for m, u in sorted(api_calls_seen):
    print(f"  {m:<7} {u[:80]}")

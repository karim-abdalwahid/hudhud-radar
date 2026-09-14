"""Follow-ups: (1) restore any takeover flipped by probe, (2) click-through ALL
settings/studio tabs' buttons, (3) validate every anchor href to an app route."""
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()
from playwright.sync_api import sync_playwright
from src.core.supabase_client import supabase_db

B = "http://localhost:8000"

# 1. restore takeover(s) flipped by probe
for l in (supabase_db.select("leads") or []):
    if l.get("human_takeover"):
        print("note: lead", l["id"][:8], "has human_takeover=True")
# owner's real lead should NOT be auto-taken-over by a probe click
leads = supabase_db.select("leads", {"facebook_account_id": "38108855985424257"}) or []
for l in leads:
    if l.get("human_takeover"):
        supabase_db.update("leads", l["id"], {"human_takeover": False})
        print("restored: Kareem lead takeover -> False")

# 2+3. tab click-throughs + anchors
anchors_bad = []
tab_failures = []
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_context(viewport={"width": 1920, "height": 1080}).new_page()
    net = []
    pg.on("response", lambda r: net.append((r.status, r.url.replace(B, ""))) if "/api/" in r.url else None)
    pg.goto(f"{B}/login"); pg.wait_for_load_state("networkidle")
    pg.fill("#loginEmail", "admin.test@hudhud.test"); pg.fill("#loginPassword", "AdminTest#2026")
    pg.click("#loginBtn"); pg.wait_for_url("**/dashboard**", timeout=15000)

    # settings tabs
    pg.goto(f"{B}/settings"); pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(1500)
    for tab in ["meta", "threads", "ai", "webhooks", "security"]:
        try:
            pg.click(f"#set-tab-{tab}")
            pg.wait_for_timeout(400)
            for bt in pg.query_selector_all(f"#set-tab-page-{tab} button:not([disabled])")[:12]:
                oc = (bt.get_attribute("onclick") or "")
                if re.search(r"disconnect|save|exchange|configure", oc, re.I) or "changeMyPassword" in oc:
                    continue
                try:
                    before = len(net)
                    bt.click(timeout=2500)
                    pg.wait_for_timeout(350)
                    for code, url in net[before:]:
                        if code >= 500 or code == 404:
                            tab_failures.append(("settings", tab, oc[:40], code, url))
                except Exception:
                    pass
        except Exception as e:
            print("settings tab switch fail:", tab, str(e)[:60])

    # studio views
    pg.goto(f"{B}/studio?view=ai"); pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(1000)
    for view in ["ai", "publisher", "queue", "feed"]:
        try:
            pg.evaluate(f"switchStudioView('{view}', false)")
            pg.wait_for_timeout(400)
            for bt in pg.query_selector_all(f"#studio-pane-{view} button:not([disabled])")[:10]:
                oc = (bt.get_attribute("onclick") or "")
                if re.search(r"publish|delete|submitPost|generate|compliance|sync|threads", oc, re.I):
                    continue
                try:
                    before = len(net)
                    bt.click(timeout=2500)
                    pg.wait_for_timeout(350)
                    for code, url in net[before:]:
                        if code >= 500 or code == 404:
                            tab_failures.append(("studio", view, oc[:40], code, url))
                except Exception:
                    pass
        except Exception as e:
            print("studio view fail:", view, str(e)[:60])

    # 3. all anchor hrefs -> route exists (live GET)
    anchors = set()
    import pathlib
    for f in list(pathlib.Path("src/templates").rglob("*.html")) + list(pathlib.Path("src/modules").rglob("*.py")):
        t = f.read_text(encoding="utf-8", errors="replace")
        anchors |= set(re.findall(r'href="(/[^"#{}$]*)"', t))
    checked = 0
    for href in sorted(a for a in anchors if not a.startswith(("/static", "/api/"))):
        try:
            r = pg.request.get(B + href, max_redirects=0, timeout=15000)
            code = r.status
        except Exception:
            code = 999
        checked += 1
        if code in (404, 500, 999):
            anchors_bad.append((href, code))
    b.close()

print(f"\nsettings/studio click failures: {len(tab_failures)}")
for t in tab_failures[:12]:
    print("   ", t)
print(f"anchors checked: {checked} | broken: {len(anchors_bad)}")
for a in anchors_bad[:15]:
    print("   ", a)

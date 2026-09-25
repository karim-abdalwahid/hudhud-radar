"""E2E reflection: inbox pill must match REAL AI pause state (the Class-D test)."""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()
from playwright.sync_api import sync_playwright

B = "http://localhost:8000"

with sync_playwright() as p:
    br = p.chromium.launch(headless=True)
    pg = br.new_context(viewport={"width": 1920, "height": 1080}).new_page()
    pg.goto(f"{B}/login"); pg.wait_for_load_state("networkidle")
    pg.fill("#loginEmail", "admin.test@hudhud.test"); pg.fill("#loginPassword", "AdminTest#2026")
    pg.click("#loginBtn"); pg.wait_for_url("**/dashboard**", timeout=15000)

    def pill():
        pg.goto(f"{B}/inbox"); pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(1800)
        return pg.inner_text("#ai-state-pill")

    print("1) default pill:", pill())

    # flip GLOBAL pause on via settings API (admin dual-write)
    r = pg.request.post(f"{B}/api/ai/pause", data={"paused": True}).json()
    print("2) after pause ON (api):", r.get("global_paused"))
    print("   pill now:", pill())

    # status endpoint truth
    st = pg.request.get(f"{B}/api/inbox/agent-status").json()
    print("3) /agent-status:", st)

    # restore
    pg.request.post(f"{B}/api/ai/pause", data={"paused": False})
    print("4) after restore pill:", pill())
    br.close()

"""E2E: AI Master Pause — toggle from settings API + real suppression."""
import asyncio, sys
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()
BASE = "http://localhost:8000"

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_context(viewport={"width": 1920, "height": 1080}).new_page()
    pg.on("pageerror", lambda e: print("[pageerror]", str(e)[:200]))

    pg.goto(f"{BASE}/login"); pg.wait_for_load_state("networkidle")
    pg.fill("#loginEmail", "admin.test@hudhud.test"); pg.fill("#loginPassword", "AdminTest#2026")
    pg.click("#loginBtn"); pg.wait_for_url("**/dashboard**", timeout=10000)
    pg.goto(f"{BASE}/settings"); pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(2500)

    # open security tab
    pg.evaluate("switchSettingsTab('security')")
    pg.wait_for_timeout(600)

    card = pg.query_selector("#btn-ai-pause")
    print("AI pause card:", "FOUND" if card else "MISSING")
    state0 = pg.evaluate("""async () => await (await fetch('/api/ai/pause')).json()""")
    print("initial:", state0)

    # toggle ON via the UI button
    pg.click("#btn-ai-pause")
    pg.wait_for_timeout(1500)
    state1 = pg.evaluate("""async () => await (await fetch('/api/ai/pause')).json()""")
    print("after UI click:", state1)
    badge = pg.evaluate("() => document.getElementById('ai-pause-badge').textContent")
    print("badge:", badge.strip())
    b.close()

# suppression proof on the real lead (Kareem, takeover=False)
from src.core.supabase_client import supabase_db
from src.agent.orchestrator import agent_orchestrator
from src.leads.models import PlatformSource

lead = (supabase_db.select("leads", {"facebook_account_id": "38108855985424257"}) or [None])[0]
print(f"\nlead takeover={lead.get('human_takeover')} (independent — global pause wins)")

async def run():
    return await agent_orchestrator.process_incoming_message_event({
        "platform": PlatformSource.FACEBOOK,
        "sender_id": "38108855985424257",
        "message_id": f"pause_e2e_{int(asyncio.get_event_loop().time()*1000) if False else 'pause_e2e_1'}",
        "text": "global pause test — AI must stay silent everywhere",
        "raw_event": {},
    })

r = asyncio.run(run())
print("orchestrator:", {k: r.get(k) for k in ("reply_sent", "ai_paused")})

# restore: toggle back OFF
from src.ai.pause import set_ai_pause
set_ai_pause(False, "190bb1d1-7d62-455c-bf62-af4eb53157e5", is_admin=True)
print("restored: AI active again")

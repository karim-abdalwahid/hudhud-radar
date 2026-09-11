"""E2E: Human Takeover — toggle persists + AI suppressed + automations silent."""
import asyncio
import sys
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
    pg.goto(f"{BASE}/inbox"); pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(3000)

    # open first conversation
    cards = pg.query_selector_all(".conv-card")
    print("conversations:", len(cards))
    if not cards:
        print("no conversations to test"); b.close(); sys.exit(1)
    cards[0].click(); pg.wait_for_timeout(1000)

    # click takeover button
    btn = pg.query_selector("#btn-takeover")
    print("takeover button:", "found" if btn else "MISSING")
    btn.click()
    pg.wait_for_timeout(2000)

    state1 = pg.evaluate("""() => ({
        banner: document.getElementById('takeover-banner').style.display,
        btnText: document.getElementById('btn-takeover').textContent.trim().slice(0, 30),
        convState: (typeof activeConvId !== 'undefined')
    })""")
    print("after click:", state1)
    b.close()

# verify DB flag persisted
from src.core.supabase_client import supabase_db
leads = supabase_db.select("leads") or []
target = leads[0]
print(f"\nDB check: lead={target['id'][:8]} human_takeover={target.get('human_takeover')}")

# verify orchestrator suppression path
from src.agent.orchestrator import agent_orchestrator
from src.leads.models import PlatformSource

event = {
    "platform": PlatformSource.FACEBOOK,
    "sender_id": target.get("facebook_account_id") or "x",
    "message_id": "takeover_test_msg",
    "text": "hello — AI should NOT reply",
    "raw_event": {},
}
result = asyncio.run(agent_orchestrator.process_incoming_message_event(event))
print("orchestrator with takeover active:", {k: result[k] for k in ("reply_sent", "human_takeover")})

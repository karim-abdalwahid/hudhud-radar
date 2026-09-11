import asyncio, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()
from src.core.supabase_client import supabase_db
from src.agent.orchestrator import agent_orchestrator
from src.leads.models import PlatformSource

leads = supabase_db.select("leads") or []
active = next((l for l in leads if l.get("human_takeover")), None)
print(f"takeover lead: {active['id'][:8]} (fb={active.get('facebook_account_id')})")

async def run():
    event = {
        "platform": PlatformSource.FACEBOOK,
        "sender_id": active.get("facebook_account_id"),
        "message_id": "takeover_verify_static_1",
        "text": "hello — AI must stay silent",
        "raw_event": {},
    }
    return await agent_orchestrator.process_incoming_message_event(event)

result = asyncio.run(run())
print("result keys:", sorted(result.keys()))
print("human_takeover:", result.get("human_takeover"), "| reply_sent:", result.get("reply_sent"))
assert result.get("human_takeover") is True and result.get("reply_sent") is None, "AI WAS NOT SUPPRESSED!"
print("\n✅ CONFIRMED: AI suppressed for this customer while takeover is active")

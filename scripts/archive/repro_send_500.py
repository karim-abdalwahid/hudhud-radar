"""Repro the manual-send 500 directly and read the REAL exception."""
import asyncio
import json
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()
from src.core.supabase_client import supabase_db
from src.modules.inbox_onboarding import _send_and_store_agent_message
from src.leads.service import lead_service

leads = supabase_db.select("leads", {"facebook_account_id": "38108855985424257"}) or []
lead = leads[0]
last_msgs = supabase_db.select("messages", {"lead_id": lead["id"]})
print("last message time:", last_msgs[-1].get("sent_at") if last_msgs else "?")
try:
    res = asyncio.run(_send_and_store_agent_message(lead, "برهان الإصلاح — رسالة بشرية"))
    print("RESULT:", res)
except Exception as e:
    print("EXC TYPE:", type(e).__name__)
    print("EXC MSG:", str(e)[:300])

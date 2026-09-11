import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()
from src.core.supabase_client import supabase_db

# 1. restore pre-test state: Kareem AI back ON (owner toggles freely from UI)
k = supabase_db.select("leads", {"facebook_account_id": "38108855985424257"}) or []
if k:
    supabase_db.update("leads", k[0]["id"], {"human_takeover": False})
    print("restored Kareem lead: human_takeover=False")

# 2. remove junk lead from the broken first test (sender 'x')
junk = supabase_db.select("leads", {"facebook_account_id": "x"}) or []
for l in junk:
    for m in (supabase_db.select("messages", {"lead_id": l["id"]}) or []):
        supabase_db.delete("messages", m["id"])
    supabase_db.delete("leads", l["id"])
    print(f"removed junk lead {l['id'][:8]} (sender 'x')")

import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()

from src.core.supabase_client import supabase_db
from src.automations.service import AutomationsService

svc = AutomationsService()  # fresh load against live Supabase
print("workflows loaded:", len(svc.list_workflows()))
rows = supabase_db.select("automations_workflows") or []
print("table rows after bootstrap:", len(rows))
for r in rows[:5]:
    print(f"  {r.get('id')} user={str(r.get('user_id'))[:8]} name={r.get('name')[:40]!r} status={r.get('status')}")

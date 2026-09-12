import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()
from src.core.supabase_client import supabase_db

rows = supabase_db.select("platform_connections", {"platform": "threads"}) or []
for r in rows:
    if r.get("account_name") == "@audit_test" or (r.get("metadata") or {}).get("platform_user_id") == "123":
        supabase_db.delete("platform_connections", r["id"])
        print(f"removed audit connection {r['id'][:8]}")
print("remaining threads connections:", len(supabase_db.select("platform_connections", {"platform": "threads"}) or []))

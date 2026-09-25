import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()
from src.core.supabase_client import supabase_db

rows = supabase_db.select("platform_connections", {"platform": "threads"}) or []
for r in rows:
    print(f"user={str(r.get('user_id'))[:8]} account={r.get('account_name')} "
          f"expires={r.get('token_expires_at')} status={r.get('status')} "
          f"token_enc={'yes' if r.get('access_token_encrypted') else 'no'}")

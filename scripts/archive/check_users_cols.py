import os, json, urllib.request, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from dotenv import load_dotenv
load_dotenv()
ref = os.getenv("SUPABASE_PROJECT_REF"); tok = os.getenv("SUPABASE_MANAGEMENT_TOKEN")
def sql(q):
    req = urllib.request.Request(
        f"https://api.supabase.com/v1/projects/{ref}/database/query",
        data=json.dumps({"query": q}).encode(), method="POST",
        headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())
cols = sql("""
SELECT column_name FROM information_schema.columns
WHERE table_schema='public' AND table_name='users' ORDER BY ordinal_position;
""")
print("users columns:", [c["column_name"] for c in cols])
rows = sql("SELECT email, role FROM public.users ORDER BY created_at;")
for r in rows:
    print(" ", r)

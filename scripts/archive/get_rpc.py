import json, os, sys, urllib.request
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
# discover the actual signature
args = sql("""
SELECT p.proname, pg_get_function_identity_arguments(p.oid) AS args, p.oid
FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
WHERE n.nspname='public' AND p.proname='match_kb_chunks';
""")
print(args)
if args:
    oid = args[0]["oid"]
    d = sql(f"SELECT pg_get_functiondef({oid}::oid) AS def;")
    print(d[0]["def"])

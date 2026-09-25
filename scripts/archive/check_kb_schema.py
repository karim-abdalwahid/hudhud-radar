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
print("=== kb_documents indexes/constraints ===")
print(sql("""
SELECT i.indexname, i.indexdef FROM pg_indexes i
WHERE i.tablename = 'kb_documents';
"""))
print("=== match_kb_chunks RPC definition (head) ===")
d = sql("SELECT prosrc FROM pg_proc WHERE proname='match_kb_chunks';")
if d and d[0].get("prosrc"):
    print(d[0]["prosrc"][:900])

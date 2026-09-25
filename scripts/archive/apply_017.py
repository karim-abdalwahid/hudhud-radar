import os, json, urllib.request, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from dotenv import load_dotenv
load_dotenv()
ref = os.getenv("SUPABASE_PROJECT_REF"); tok = os.getenv("SUPABASE_MANAGEMENT_TOKEN")
sql = open("database/migrations/017_kb_per_user.sql", encoding="utf-8").read()
req = urllib.request.Request(
    f"https://api.supabase.com/v1/projects/{ref}/database/query",
    data=json.dumps({"query": sql}).encode(), method="POST",
    headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        print("OK", r.status, r.read().decode()[:200])
except urllib.error.HTTPError as e:
    print("HTTP", e.code, "->", e.read().decode()[:500])

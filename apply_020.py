import json, os, sys, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from dotenv import load_dotenv
load_dotenv()
ref = os.getenv("SUPABASE_PROJECT_REF"); tok = os.getenv("SUPABASE_MANAGEMENT_TOKEN")
sql = open("database/migrations/020_platform_enum_manual_other.sql", encoding="utf-8").read()
req = urllib.request.Request(f"https://api.supabase.com/v1/projects/{ref}/database/query",
    data=json.dumps({"query": sql}).encode(), method="POST",
    headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        print("Migration 020 applied:", r.status)
except urllib.error.HTTPError as e:
    print("HTTP", e.code, e.read().decode()[:250])
# verify
req2 = urllib.request.Request(f"https://api.supabase.com/v1/projects/{ref}/database/query",
    data=json.dumps({"query": "SELECT enumlabel FROM pg_enum e JOIN pg_type t ON t.oid=e.enumtypid WHERE t.typname='platform_enum'"}).encode(),
    method="POST", headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
with urllib.request.urlopen(req2, timeout=30) as r:
    print("platform_enum now:", sorted(x["enumlabel"] for x in json.loads(r.read().decode())))

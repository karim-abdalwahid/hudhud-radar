import json, os, sys, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from dotenv import load_dotenv
load_dotenv()
ref = os.getenv("SUPABASE_PROJECT_REF"); tok = os.getenv("SUPABASE_MANAGEMENT_TOKEN")
sql = open("database/migrations/024_coupons_polar_discount.sql", encoding="utf-8").read()
req = urllib.request.Request(f"https://api.supabase.com/v1/projects/{ref}/database/query",
    data=json.dumps({"query": sql}).encode(), method="POST",
    headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        print("Migration 024 applied:", r.status)
except urllib.error.HTTPError as e:
    print("HTTP", e.code, e.read().decode()[:250])
# verify
req2 = urllib.request.Request(f"https://api.supabase.com/v1/projects/{ref}/database/query",
    data=json.dumps({"query": "SELECT column_name, data_type FROM information_schema.columns WHERE table_name='coupons' AND column_name='polar_discount_id'"}).encode(),
    method="POST", headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req2, timeout=30) as r:
        rows = json.loads(r.read().decode())
        print("coupons.polar_discount_id present:", bool(rows), rows)
except urllib.error.HTTPError as e:
    print("Verify HTTP", e.code, e.read().decode()[:250])
import os
import sys
import json
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from dotenv import load_dotenv
load_dotenv()
ref = os.getenv("SUPABASE_PROJECT_REF"); tok = os.getenv("SUPABASE_MANAGEMENT_TOKEN")
sql = open("database/migrations/019_automations_id_text.sql", encoding="utf-8").read()
req = urllib.request.Request(
    f"https://api.supabase.com/v1/projects/{ref}/database/query",
    data=json.dumps({"query": sql}).encode(), method="POST",
    headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        print("Migration 019 applied:", r.status)
except urllib.error.HTTPError as e:
    print("HTTP", e.code, e.read().decode()[:300])

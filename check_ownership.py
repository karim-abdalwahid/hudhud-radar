import os, sys, json, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from dotenv import load_dotenv
load_dotenv()
SUPA_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPA_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY", "")

def q(table, params):
    url = f"{SUPA_URL}/rest/v1/{table}?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())

import urllib.parse

print("=== USERS (all) ===")
for u in q("users", {"select": "id,email,role", "order": "created_at.desc", "limit": "10"}):
    print(f"  {u.get('email')}  role={u.get('role')}  id={str(u.get('id'))[:8]}...")

print("\n=== LEADS columns sample ===")
sample = q("leads", {"select": "*", "limit": "1"})
if sample:
    print(f"  Columns: {', '.join(sample[0].keys())}")

print("\n=== LEADS (latest 10) ===")
for l in q("leads", {"select": "*", "order": "created_at.desc", "limit": "10"}):
    uid = l.get("user_id")
    print(f"  user_id={str(uid)[:8] or 'NULL!'}  platform={l.get('platform') or l.get('source_platform')}  name={l.get('contact_name') or l.get('name') or l.get('username')}  at {l.get('created_at')}")

print("\n=== MESSAGES columns sample ===")
msample = q("messages", {"select": "*", "limit": "1"})
if msample:
    print(f"  Columns: {', '.join(msample[0].keys())}")

print("\n=== MESSAGES (latest 10) ===")
for m in q("messages", {"select": "*", "order": "created_at.desc", "limit": "10"}):
    uid = m.get("user_id")
    print(f"  user_id={str(uid)[:8] or 'NULL!'}  sender={m.get('sender_type')}  lead={str(m.get('lead_id'))[:8]}  text={str(m.get('content'))[:40]!r}  at {m.get('created_at')}")

print("\n=== NULL user_id counts ===")
for t in ["leads", "messages"]:
    rows = q(t, {"select": "id,user_id", "user_id": "is.null"})
    print(f"  {t}: {len(rows)} rows with NULL user_id")

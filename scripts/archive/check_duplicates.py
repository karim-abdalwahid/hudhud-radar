import os, json, urllib.request, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from dotenv import load_dotenv
load_dotenv()
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY"); base = os.getenv("SUPABASE_URL").rstrip("/")
H = {"apikey": key, "Authorization": "Bearer " + key}
def q(table, params=""):
    req = urllib.request.Request(base + "/rest/v1/" + table + params, headers=H)
    with urllib.request.urlopen(req, timeout=15) as r: return json.loads(r.read().decode())
users = q("users", "?select=id,email,role,created_at&order=created_at.asc")
conns = q("platform_connections", "?select=user_id,platform")
notifs = q("notifications", "?select=user_id")
subs = q("user_subscriptions", "?select=user_id")
print("=== USERS ===")
for u in users:
    uid = u["id"]
    my_conns = [c["platform"] for c in conns if c["user_id"] == uid]
    my_notifs = sum(1 for n in notifs if n["user_id"] == uid)
    my_subs = sum(1 for s in subs if s["user_id"] == uid)
    print(f"{u['email']:<32} role={u['role']:<7} created={u['created_at'][:10]} id={uid}")
    print(f"   connections={my_conns}  notifications={my_notifs}  subscriptions={my_subs}")

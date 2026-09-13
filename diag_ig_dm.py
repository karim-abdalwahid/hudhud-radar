"""IG DM delivery diagnostics: what arrived? what's subscribed?"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()

TOKEN = os.getenv("META_PAGE_ACCESS_TOKEN")
IG_ID = os.getenv("META_INSTAGRAM_ACCOUNT_ID")
G = "https://graph.facebook.com/v21.0"


def g(method, node, params=None, data=None):
    params = dict(params or {})
    params["access_token"] = TOKEN
    qs = urllib.parse.urlencode(params)
    url = f"{G}/{node}?{qs}"
    req = urllib.request.Request(url, data=b"" if method == "POST" else None, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:250]


print("== 1. IG account subscribed_apps ==")
s, d = g("GET", f"{IG_ID}/subscribed_apps", {"fields": "id,name,subscribed_fields"})
print(s, json.dumps(d, ensure_ascii=False)[:400])

print("\n== 2. what the app's webhook actually received recently (processed_events) ==")
from src.core.supabase_client import supabase_db
evs = supabase_db.select("processed_events") or []
evs.sort(key=lambda e: e.get("processed_at") or "", reverse=True)
for e in evs[:8]:
    print(f"  {e.get('processed_at')} [{e.get('event_type')}] {str(e.get('event_key'))[:70]}")
if not evs:
    print("  (none ever!)")

print("\n== 3. leads/messages last 5 ==")
for l in (supabase_db.select("leads") or [])[-5:]:
    print(f"  lead {l['id'][:8]} src={l.get('source')} name={l.get('full_name')} ig={l.get('instagram_account_id')} created={l.get('created_at')}")
for m in (supabase_db.select("messages") or [])[-5:]:
    print(f"  msg [{m.get('platform')}] {str(m.get('content'))[:40]!r} at {m.get('created_at')}")

print("\n== 4. app-level: conversations check on the IG account ==")
s, d = g("GET", f"{IG_ID}/conversations", {"fields": "participants,messages{message,created_time}", "limit": 3})
print(s, str(d)[:350])

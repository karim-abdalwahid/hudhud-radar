"""Live: subscribe the mentions field on the real Page + signed end-to-end
mention simulation to production -> verify CRM row -> cleanup."""
import hmac
import hashlib
import json
import os
import sys
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from dotenv import load_dotenv
load_dotenv()

APP_SECRET = os.getenv("META_APP_SECRET", "")
PAGE_ID = os.getenv("META_PAGE_ID", "")
PAGE_TOKEN = os.getenv("META_PAGE_ACCESS_TOKEN", "")
BASE_URL = os.getenv("APP_BASE_URL", "https://www.hudhd.com").rstrip("/")
GRAPH = "https://graph.facebook.com/v21.0"
SUPA_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPA_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY", "")


def graph_post(path, params):
    url = f"{GRAPH}/{path}?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, data=b"", method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": e.read().decode()[:200]}


def rest(q, method="GET", body=None):
    req = urllib.request.Request(
        f"{SUPA_URL}/rest/v1/{q}",
        data=json.dumps(body).encode() if body is not None else None,
        method=method,
        headers={"apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}",
                 "Content-Type": "application/json", "Prefer": "return=representation"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode() or "[]")


print("== 1. subscribe mentions field on the Page ==")
r = graph_post(f"{PAGE_ID}/subscribed_apps",
               {"subscribed_fields": "feed,messages,messaging_postbacks,messaging_referrals,mention",
                "access_token": PAGE_TOKEN})
print("subscribe result:", json.dumps(r)[:200])

print("\n== 2. verify subscribed fields live ==")
url = f"{GRAPH}/{PAGE_ID}/subscribed_apps?" + urllib.parse.urlencode(
    {"access_token": PAGE_TOKEN, "fields": "id,name,subscribed_fields"})
with urllib.request.urlopen(url, timeout=15) as resp:
    apps = json.loads(resp.read().decode()).get("data", [])
for a in apps:
    print(f"  {a.get('name')}: {a.get('subscribed_fields')}")

print("\n== 3. signed mention simulation to production webhook ==")
payload = {
    "object": "page",
    "entry": [{
        "id": PAGE_ID,
        "time": 1700000000000,
        "changes": [{
            "field": "mentions",
            "value": {
                "item": "comment",
                "comment_id": f"audit_mention_{os.urandom(3).hex()}",
                "post_id": "audit_post_1",
                "message": "shoutout to the best page ever!",
                "from": {"id": "audit_mentioner_9", "name": "Audit Fan"},
            },
        }],
    }],
}
body = json.dumps(payload).encode()
sig = "sha256=" + hmac.new(APP_SECRET.encode(), body, hashlib.sha256).hexdigest()
req = urllib.request.Request(
    f"{BASE_URL}/api/webhook/meta",
    data=body,
    headers={"Content-Type": "application/json", "X-Hub-Signature-256": sig},
    method="POST")
try:
    with urllib.request.urlopen(req, timeout=20) as resp:
        print("  webhook:", resp.status, resp.read().decode()[:160])
except urllib.error.HTTPError as e:
    print("  webhook HTTP", e.code, e.read().decode()[:160])

import time
time.sleep(6)

print("\n== 4. verify CRM row ==")
leads = rest("leads?facebook_account_id=eq.audit_mentioner_9&select=id,full_name,facebook_account_id")
print("  mention leads:", [(l["id"][:8], l.get("full_name")) for l in leads])
if leads:
    msgs = rest(f"messages?lead_id=eq.{leads[0]['id']}&select=content,platform_message_id,metadata")
    for m in msgs:
        print(f"  message: {m.get('content')!r} meta={m.get('metadata')}")

    print("\n== 5. cleanup audit rows ==")
    for m in msgs:
        mid = rest(f"messages?lead_id=eq.{leads[0]['id']}&select=id")
    for row in mid:
        rest(f"messages?id=eq.{row['id']}", method="DELETE")
    rest(f"leads?id=eq.{leads[0]['id']}", method="DELETE")
    print("  audit lead + messages deleted")
print("\nDONE")

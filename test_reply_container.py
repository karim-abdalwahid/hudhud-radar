"""Perform the REAL threads_manage_replies API test call: publish a reply
via the official container flow (reply_to_id) — the correct Threads API path."""
import json
import sys
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()
from src.meta_api.extended_api import threads_leads_sync

TOKEN = threads_leads_sync._resolve_token("8d0ab6c3-544d-4a14-84c9-d021acf26ddf")
TG = "https://graph.threads.net/v1.0"
TARGET = "18116660710767178"  # the owner's coffee-pricing thread


def call(method, node, params=None):
    qs = urllib.parse.urlencode(params or {})
    req = urllib.request.Request(f"{TG}/{node}?{qs}", data=b"", method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:400]


print("== 1. resolve threads user id ==")
s, me = call("GET", "me", {"fields": "id,username", "access_token": TOKEN})
print(" ", s, json.dumps(me, ensure_ascii=False)[:120])
uid = me.get("id")

print("\n== 2. create reply container (media_type=TEXT + reply_to_id) ==")
s, c = call("POST", f"{uid}/threads", {
    "media_type": "TEXT",
    "text": "شكراً لتواصلك! فريق Hudhud 🧡",
    "reply_to_id": TARGET,
    "access_token": TOKEN,
})
print(" ", s, json.dumps(c, ensure_ascii=False)[:200])
container = c.get("id") if s == 200 else None

print("\n== 3. publish the reply container ==")
if container:
    import time
    for _ in range(5):
        s, p = call("POST", f"{uid}/threads_publish",
                    {"creation_id": container, "access_token": TOKEN})
        if s == 200:
            break
        time.sleep(2)
    print(" ", s, json.dumps(p, ensure_ascii=False)[:200])
    print("\n=== RESULT ===")
    print("threads_manage_replies API test call:", "PASSED ✅ (HTTP 200)" if s == 200 else "FAILED ❌")

"""Debug threads reply POST: full error body + alternative correct shapes."""
import json
import os
import sys
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from dotenv import load_dotenv
load_dotenv()
sys.path.insert(0, ".")
from src.meta_api.extended_api import threads_leads_sync

TOKEN = threads_leads_sync._resolve_token("8d0ab6c3-544d-4a14-84c9-d021acf26ddf")
TG = "https://graph.threads.net/v1.0"


def call(method, node, params=None):
    qs = urllib.parse.urlencode(params or {})
    req = urllib.request.Request(f"{TG}/{node}?{qs}", data=b"", method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:500]


s, r = call("GET", "me/threads", {"fields": "id,text,timestamp,is_reply", "limit": 5,
                                  "access_token": TOKEN})
print("threads:", json.dumps(r, ensure_ascii=False)[:600])
threads = r.get("data", [])

for t in threads[:3]:
    tid = t["id"]
    s, r = call("POST", f"{tid}/replies",
                {"access_token": TOKEN, "text": "شكراً لتواصلك! فريق Hudhud 🧡"})
    print(f"\nPOST /{tid}/replies -> {s}")
    print("   body:", json.dumps(r, ensure_ascii=False)[:400])

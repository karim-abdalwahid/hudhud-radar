"""Perform the REQUIRED API test calls for threads_manage_replies +
instagram_business_manage_comments (live, verifiable 200s on the exact endpoints)."""
import json
import sys
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from dotenv import load_dotenv
load_dotenv()

import os
PAGE_TOKEN = os.getenv("META_PAGE_ACCESS_TOKEN", "")
IG_ID = os.getenv("META_INSTAGRAM_ACCOUNT_ID", "")
G = "https://graph.facebook.com/v21.0"
TG = "https://graph.threads.net/v1.0"


def call(method, url, params=None, data=None):
    params = dict(params or {})
    if data is not None:
        params.update(data)
    qs = urllib.parse.urlencode(params)
    req = urllib.request.Request(f"{url}?{qs}", data=b"", method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:250]


sys.path.insert(0, ".")
from src.meta_api.extended_api import threads_leads_sync
OWNER = "8d0ab6c3-544d-4a14-84c9-d021acf26ddf"
THREADS_TOKEN = threads_leads_sync._resolve_token(OWNER)
results = []

print("===== A. threads_manage_replies =====")
print("threads token resolved:", bool(THREADS_TOKEN))

s, r = call("GET", f"{TG}/me/threads",
            {"fields": "id,text,timestamp", "limit": 5, "access_token": THREADS_TOKEN})
results.append(("A1 GET /me/threads", s))
print(f"A1 GET /me/threads -> {s}")
threads = r.get("data", []) if isinstance(r, dict) else []
target = threads[0]["id"] if threads else None
print("   target thread:", target)

replies = []
if target:
    s, r = call("GET", f"{TG}/{target}/replies",
                {"fields": "id,text,timestamp,username", "limit": 10,
                 "access_token": THREADS_TOKEN})
    results.append((f"A2 GET /{target}/replies", s))
    print(f"A2 GET replies -> {s} | replies:", len(r.get("data", [])) if isinstance(r, dict) else 0)

    s, r = call("POST", f"{TG}/{target}/replies",
                {"access_token": THREADS_TOKEN, "text": "شكراً لتواصلك! فريق Hudhud 🧡"})
    results.append((f"A3 POST /{target}/replies", s))
    print(f"A3 POST reply -> {s} :: {json.dumps(r)[:120]}")
    reply_id = r.get("id") if isinstance(r, dict) else None

    if reply_id:
        s, r = call("POST", f"{TG}/{reply_id}/replies",
                    {"access_token": THREADS_TOKEN, "text": "تحت أمرك دائماً! 🧡"})
        results.append((f"A4 POST /{reply_id}/replies (reply-to-reply)", s))
        print(f"A4 POST reply-to-reply -> {s}")

print("\n===== B. instagram_business_manage_comments =====")
s, r = call("GET", f"{G}/{IG_ID}/media",
            {"fields": "id,media_product_type", "limit": 3, "access_token": PAGE_TOKEN})
results.append((f"B1 GET /{IG_ID}/media", s))
print(f"B1 GET media -> {s}")
media = r.get("data", []) if isinstance(r, dict) else []
mid = media[0]["id"] if media else None
print("   target media:", mid)

comment_id = None
if mid:
    s, r = call("POST", f"{G}/{mid}/comments",
                {"access_token": PAGE_TOKEN,
                 "message": "شكراً لمتابعتكم! اسألوا عن أي خدمة في الكومنتات 💬"})
    results.append((f"B2 POST /{mid}/comments", s))
    print(f"B2 POST comment -> {s} :: {json.dumps(r)[:120]}")
    comment_id = r.get("id") if isinstance(r, dict) else None

    s, r = call("GET", f"{G}/{mid}/comments",
                {"fields": "id,text,username", "limit": 5, "access_token": PAGE_TOKEN})
    results.append((f"B3 GET /{mid}/comments", s))
    print(f"B3 GET comments -> {s} | count:", len(r.get("data", [])) if isinstance(r, dict) else 0)

    if not comment_id:
        cs = r.get("data", []) if isinstance(r, dict) else []
        comment_id = cs[0]["id"] if cs else None
    if comment_id:
        s, r = call("POST", f"{G}/{comment_id}/replies",
                    {"access_token": PAGE_TOKEN,
                     "message": "تحت أمرك! لو محتاج تفاصيل كلمنا هنا 🧡"})
        results.append((f"B4 POST /{comment_id}/replies", s))
        print(f"B4 POST reply-to-comment -> {s}")

print("\n===== SUMMARY =====")
all_ok = True
for name, code in results:
    ok = code == 200
    all_ok = all_ok and ok
    print(f"  {'✅' if ok else '❌'} {name} -> {code}")
print("\nALL REQUIRED API TEST CALLS:", "PASSED ✅" if all_ok and results else "INCOMPLETE ❌")

"""Attempt IG account subscription the correct ways; report each outcome."""
import json
import os
import sys
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()
TOKEN = os.getenv("META_PAGE_ACCESS_TOKEN")
IG_ID = os.getenv("META_INSTAGRAM_ACCOUNT_ID")
G = "https://graph.facebook.com/v21.0"

def call(method, node, params=None):
    params = dict(params or {})
    params["access_token"] = TOKEN
    url = f"{G}/{node}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, data=b"" if method == "POST" else None, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:260]

print("A. GET subscribed_apps (no fields):")
print("  ", *call("GET", f"{IG_ID}/subscribed_apps"))

print("\nB. POST subscribe messages,comments,mentions:")
print("  ", *call("POST", f"{IG_ID}/subscribed_apps", {"subscribed_fields": "messages,comments,mentions"}))

print("\nC. confirm via page conversations endpoint works for IG id listing:")
print("  ", *call("GET", f"{IG_ID}", {"fields": "id,username,name,followers_count"}))

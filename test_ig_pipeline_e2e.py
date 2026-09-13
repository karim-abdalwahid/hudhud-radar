"""1) Clean leftover evt-x. 2) Prove OUR instagram-object pipeline end-to-end:
signed POST to production webhook with object=instagram -> lead+msg created -> cleanup."""
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()
from src.core.supabase_client import supabase_db

# 1. leftover cleanup
left = supabase_db.select("processed_events", {"event_key": "evt-x"}) or []
for row in left:
    supabase_db.delete("processed_events", row["id"])
print("leftover evt-x removed:", len(left))

# 2. instagram-object simulation
secret = os.getenv("META_APP_SECRET", "")
tag = f"ig_probe_{int(time.time())}"
payload = {"object": "instagram", "entry": [{
    "id": os.getenv("META_INSTAGRAM_ACCOUNT_ID"),
    "time": int(time.time()),
    "messaging": [{
        "sender": {"id": tag, "username": "probe_customer"},
        "recipient": {"id": os.getenv("META_INSTAGRAM_ACCOUNT_ID")},
        "timestamp": int(time.time() * 1000),
        "message": {"mid": tag + "_m1", "text": "مهتم بالخدمة - برهان مسار IG"},
    }],
}]}
raw = json.dumps(payload).encode()
sig = "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
req = urllib.request.Request("https://www.hudhd.com/api/webhook/meta", data=raw, method="POST",
                             headers={"Content-Type": "application/json", "X-Hub-Signature-256": sig})
try:
    with urllib.request.urlopen(req, timeout=25) as r:
        print("webhook:", r.status, r.read().decode()[:120])
except urllib.error.HTTPError as e:
    print("webhook HTTP", e.code, e.read().decode()[:160])

time.sleep(8)
leads = supabase_db.select("leads", {"instagram_account_id": tag}) or []
msgs = supabase_db.select("messages", {"platform_message_id": tag + "_m1"}) or []
print(f"CRM after IG event -> leads: {len(leads)} messages: {len(msgs)}")
if leads:
    l = leads[0]
    print(f"  lead src={l.get('source')} username={l.get('username')}")
if msgs:
    m = msgs[0]
    print(f"  msg platform={m.get('platform')} sender={m.get('sender_type')} text={str(m.get('content'))[:40]!r}")
    # agent reply attempted?
    replies = [x for x in (supabase_db.select("messages", {"lead_id": l["id"]}) or []) if x.get("sender_type") != "lead"]
    print(f"  AI replies stored: {len(replies)}", (str(replies[0].get('content'))[:60] if replies else ""))

# cleanup probe rows
for m in (supabase_db.select("messages", {"platform_message_id": tag + "_m1"}) or []):
    supabase_db.delete("messages", m["id"])
for l in (supabase_db.select("leads", {"instagram_account_id": tag}) or []):
    supabase_db.delete("leads", l["id"])
for r in (supabase_db.select("processed_events", {"event_key": "like." + tag}) or []):
    supabase_db.delete("processed_events", r["id"])
# dedup keys use message mid -> remove by prefix via REST-like scan
evs = supabase_db.select("processed_events") or []
for e in evs:
    if tag in (e.get("event_key") or ""):
        supabase_db.delete("processed_events", e["id"])
print("probe cleaned")

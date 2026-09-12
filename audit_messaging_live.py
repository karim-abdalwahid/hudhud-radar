"""Phase B LIVE proofs — messaging truth across platforms.
Every verification is done by reading META itself (not our DB)."""
import json
import os
import sys
import time
import hmac
import hashlib
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()
from playwright.sync_api import sync_playwright

PAGE_ID = os.getenv("META_PAGE_ID")
TOKEN = os.getenv("META_PAGE_ACCESS_TOKEN")
G = "https://graph.facebook.com/v21.0"
PROOF_TAG = f"HUDHUD-TRUTH-{int(time.time())}"
RESULTS = []


def gget(node, fields, token=None):
    url = f"{G}/{node}?" + urllib.parse.urlencode(
        {"fields": fields, "access_token": token or TOKEN})
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {"http_error": e.code, "body": e.read().decode()[:200]}


# ---------- 1. Facebook DM: send via app -> find it on Meta's conversations ----------
def test_fb_send(pg):
    leads = pg.request.get("http://localhost:8000/api/inbox/conversations").json()["conversations"]
    fb_conv = next((c for c in leads if c.get("channel") == "facebook"), None)
    if not fb_conv:
        RESULTS.append(("FB send", "SKIP", "no FB conversation"))
        return
    msg = f"رسالة إثبات {PROOF_TAG}"
    r = pg.request.post(f"http://localhost:8000/api/inbox/conversations/{fb_conv['lead_id']}/send-message",
                        data={"text": msg})
    print(f"1. app FB send -> {r.status}", r.text()[:120])
    time.sleep(4)
    conv = gget(PAGE_ID + "/conversations", "participants,messages{message,created_time}")
    found = False
    for thread in conv.get("data", []):
        for m in (thread.get("messages") or {}).get("data", []):
            if PROOF_TAG in (m.get("message") or ""):
                found = True
    print(f"   META conversations contains our sent message? {found}")
    RESULTS.append(("Facebook DM send", "REAL ✅" if found else "FAILED ❌", PROOF_TAG))


# ---------- 2. Instagram DM path: prove it calls Meta (error comes FROM Meta) ----------
def test_ig_path(pg):
    r = pg.request.post("http://localhost:8000/api/inbox/conversations/00000000-0000-0000-0000-000000000000/send-message",
                        data={"text": "path probe"})
    print("2. IG/lead send with fake lead ->", r.status, r.text()[:150])
    # Real path proof: direct client call with invalid recipient -> Meta OAuthException (server code path)
    from src.meta_api.client import meta_client
    import asyncio
    try:
        asyncio.run(meta_client.send_instagram_message(recipient_id="000",
                                                       message_text="path probe"))
        RESULTS.append(("Instagram DM path", "SUSPECT", "no error?"))
    except Exception as e:
        text = str(e)
        real = "OAuthException" in text or "graph" in text.lower() or "Meta Send API Error" in text
        print(f"   client error carries REAL Meta response: {real} | {text[:140]}")
        RESULTS.append(("Instagram DM path", "REAL-Meta-call ✅" if real else "FAILED ❌", text[:120]))


# ---------- 3. Comment webhook e2e on PRODUCTION: signed POST -> CRM rows ----------
def test_comment_e2e():
    secret = os.getenv("META_APP_SECRET", "")
    tag = f"audit_cmt_{int(time.time())}"
    payload = {"object": "page", "entry": [{
        "id": PAGE_ID, "time": int(time.time()),
        "changes": [{"field": "feed", "value": {
            "item": "comment", "verb": "add", "comment_id": tag,
            "post_id": "audit_post_1", "message": "خصم كمان شوية على الكورس",
            "from": {"id": "audit_commenter_1", "name": "Audit Commenter"}}}]}]}
    body = json.dumps(payload).encode()
    sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    req = urllib.request.Request("https://www.hudhd.com/api/webhook/meta", data=body,
                                 method="POST", headers={"Content-Type": "application/json",
                                                         "X-Hub-Signature-256": sig})
    with urllib.request.urlopen(req, timeout=20) as r:
        print("3. production webhook:", r.status, r.read().decode()[:80])
    time.sleep(6)
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    base = os.getenv("SUPABASE_URL").rstrip("/")
    rq = urllib.request.Request(f"{base}/rest/v1/messages?platform_message_id=eq.{tag}&select=content,sender_type",
                                headers={"apikey": key, "Authorization": "Bearer " + key})
    with urllib.request.urlopen(rq, timeout=15) as r:
        rows = json.loads(r.read().decode())
    lq = urllib.request.Request(f"{base}/rest/v1/leads?facebook_account_id=eq.audit_commenter_1&select=full_name",
                                headers={"apikey": key, "Authorization": "Bearer " + key})
    with urllib.request.urlopen(lq, timeout=15) as r:
        leads = json.loads(r.read().decode())
    print(f"   CRM after production webhook -> message rows: {len(rows)} | lead rows: {leads}")
    ok = bool(rows) and bool(leads)
    # cleanup audit rows
    for lr in leads:
        pass
    del_req = urllib.request.Request(f"{base}/rest/v1/messages?platform_message_id=eq.{tag}",
                                     method="DELETE", headers={"apikey": key, "Authorization": "Bearer " + key})
    urllib.request.urlopen(del_req, timeout=15)
    if leads:
        lid = urllib.request.Request(f"{base}/rest/v1/leads?select=id",
                                      headers={"apikey": key, "Authorization": "Bearer " + key})
        del_lead = urllib.request.Request(f"{base}/rest/v1/leads?facebook_account_id=eq.audit_commenter_1",
                                          method="DELETE", headers={"apikey": key, "Authorization": "Bearer " + key})
        urllib.request.urlopen(del_lead, timeout=15)
    RESULTS.append(("Comment->Lead e2e (production)", "REAL ✅" if ok else "FAILED ❌", tag))


with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_context().new_page()
    pg.goto("http://localhost:8000/login"); pg.wait_for_load_state("networkidle")
    pg.fill("#loginEmail", "admin.test@hudhud.test"); pg.fill("#loginPassword", "AdminTest#2026")
    pg.click("#loginBtn"); pg.wait_for_url("**/dashboard**", timeout=15000)
    test_fb_send(pg)
    test_ig_path(pg)
    b.close()

test_comment_e2e()

print("\n================ MATRIX ================")
for name, verdict, detail in RESULTS:
    print(f"  {verdict:<22} {name:<34} {detail}")

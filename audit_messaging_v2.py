"""Phase B proof v2: IG path (bare asyncio), FB HUMAN_AGENT send -> verify on Meta."""
import asyncio
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

PAGE_ID = os.getenv("META_PAGE_ID")
TOKEN = os.getenv("META_PAGE_ACCESS_TOKEN")
G = "https://graph.facebook.com/v21.0"
PROOF = f"HUDHUD-TRUTH2-{int(time.time())}"
results = []

# ---- IG path proof (real HTTP to Meta; error strings come FROM Meta) ----
async def ig_probe():
    from src.meta_api.client import meta_client
    try:
        await meta_client.send_instagram_message(recipient_id="000000", message_text="path probe",
                                                 messaging_type=None)
        return "UNEXPECTED SUCCESS"
    except Exception as e:
        return str(e)[:250]

ig_err = asyncio.run(ig_probe())
real = ("OAuthException" in ig_err or "Meta" in ig_err)
print(f"1. IG DM path reaches Meta? {real} | sample error from Meta: {ig_err[:150]}")
results.append(("Instagram DM path", "REAL-Meta-call ✅" if real else "FAILED ❌"))

with __import__("playwright.sync_api", fromlist=["sync_playwright"]).sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_context().new_page()
    pg.goto("http://localhost:8000/login"); pg.wait_for_load_state("networkidle")
    pg.fill("#loginEmail", "admin.test@hudhud.test"); pg.fill("#loginPassword", "AdminTest#2026")
    pg.click("#loginBtn"); pg.wait_for_url("**/dashboard**", timeout=15000)

    convs = pg.request.get("http://localhost:8000/api/inbox/conversations").json()["conversations"]
    fb = next((c for c in convs if c.get("channel") == "facebook"), None)
    r = pg.request.post(f"http://localhost:8000/api/inbox/conversations/{fb['lead_id']}/send-message",
                        data={"text": f"رسالة إثبات {PROOF}"})
    print(f"2. FB manual send (HUMAN_AGENT) -> {r.status} {r.text()[:150]}")
    ok_send = r.status == 200
    b.close()

if ok_send:
    time.sleep(5)
    url = f"{G}/{PAGE_ID}/conversations?" + urllib.parse.urlencode(
        {"fields": "messages{message,created_time}", "limit": 10, "access_token": TOKEN})
    with urllib.request.urlopen(url, timeout=20) as resp:
        data = json.loads(resp.read().decode()).get("data", [])
    found = any(PROOF in (m.get("message") or "") for t in data for m in (t.get("messages") or {}).get("data", []))
    print(f"   META conversations contains it? {found}")
    results.append(("Facebook human send >24h", "REAL ✅" if found else "SENT-but-unverified ⚠️"))
else:
    results.append(("Facebook human send >24h", "REJECTED BY META ❌"))

print("\n===== MATRIX =====")
for n, v in results:
    print(f"  {v:<20} {n}")

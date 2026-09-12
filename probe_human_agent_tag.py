"""Probe: the sanctioned HUMAN_AGENT message tag (messaging_type=MESSAGE_TAG)."""
import json, os, sys, time, urllib.parse, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()
TOKEN = os.getenv("META_PAGE_ACCESS_TOKEN")
RECIPIENT = "38108855985424257"  # Kareem (the owner's own alt - consented test)
PROOF = f"HUDHUD-HUMANAGENT-{int(time.time())}"

body = {
    "recipient": {"id": RECIPIENT},
    "message": {"text": f"🧪 رسالة إثبات Human Agent {PROOF}"},
    "messaging_type": "MESSAGE_TAG",
    "tag": "HUMAN_AGENT",
}
url = "https://graph.facebook.com/v21.0/me/messages?" + urllib.parse.urlencode({"access_token": TOKEN})
req = urllib.request.Request(url, data=json.dumps(body).encode(),
                             headers={"Content-Type": "application/json"}, method="POST")
try:
    with urllib.request.urlopen(req, timeout=20) as r:
        print("Meta accepted HUMAN_AGENT tag:", r.status, r.read().decode()[:200])
except urllib.error.HTTPError as e:
    print("Meta rejected:", e.code, e.read().decode()[:300])

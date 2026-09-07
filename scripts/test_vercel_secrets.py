"""Test which secret the production instance signs with (from pulled Vercel env)."""
import base64
import hashlib
import hmac
import json
import os

import httpx
from dotenv import load_dotenv

load_dotenv(".vercel/.env.production", override=True)
ts = os.getenv("THREADS_APP_SECRET", "")
ms = os.getenv("META_APP_SECRET", "")
print("Vercel THREADS secret prefix:", ts[:12] if ts else "MISSING")
print("Vercel META secret prefix:", ms[:12] if ms else "MISSING")

BASE = os.environ.get("APP_BASE_URL", "https://hudhud-radar.vercel.app")
for name, sec in [("threads", ts), ("meta", ms)]:
    if not sec:
        continue
    payload = base64.urlsafe_b64encode(
        json.dumps({"user_id": "th-test", "algorithm": "HMAC-SHA256"}).encode()
    )
    sig = base64.urlsafe_b64encode(hmac.new(sec.encode(), payload, hashlib.sha256).digest())
    sr = sig.decode() + "." + payload.decode()
    r = httpx.post(f"{BASE}/api/data-deletion", data={"signed_request": sr}, timeout=60)
    print(f"{name} secret ->", r.status_code, r.json())

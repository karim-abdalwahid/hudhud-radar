"""Debug: verify which secret the production instance actually holds by
checking env source of truth, then test signature locally."""
import base64
import hashlib
import hmac
import json
import os
import sys

sys.path.insert(0, ".")

import httpx
from dotenv import load_dotenv

load_dotenv()

from src.config import settings  # noqa: E402

print("Local THREADS_APP_SECRET:", (settings.THREADS_APP_SECRET or "")[:12])
print("Local META_APP_SECRET:", (settings.META_APP_SECRET or "")[:12])

# Vercel env values (the deployed instance uses these)
from vercel_env import THREADS_SECRET_ON_VERCEL  # noqa: E402  (created below)

payload = base64.urlsafe_b64encode(
    json.dumps({"user_id": "th-user-test", "algorithm": "HMAC-SHA256"}).encode()
)
sig = base64.urlsafe_b64encode(hmac.new(THREADS_SECRET_ON_VERCEL.encode(), payload, hashlib.sha256).digest())
sr = sig.decode() + "." + payload.decode()
r = httpx.post(
    "https://hudhud-radar.vercel.app/api/data-deletion",
    data={"signed_request": sr}, timeout=60,
)
print("with vercel threads secret:", r.status_code, r.json())

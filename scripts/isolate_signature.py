"""Isolate the signed_request verification: local test of the exact algorithm
used in compliance_pages.py, then compare against deployed behavior."""
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

THREADS_SECRET = os.getenv("THREADS_APP_SECRET", "")
print("Local threads secret len:", len(THREADS_SECRET))

# Build a signed_request exactly like Meta does
payload_obj = {"user_id": "th-test", "algorithm": "HMAC-SHA256"}
payload_b64 = base64.urlsafe_b64encode(json.dumps(payload_obj).encode()).decode().rstrip("=")
sig = hmac.new(THREADS_SECRET.encode(), payload_b64.encode("ascii"), hashlib.sha256).digest()
sig_b64 = base64.urlsafe_b64encode(sig).decode().rstrip("=")
signed_request = f"{sig_b64}.{payload_b64}"

# Verify with the exact same code path as production
enc_sig, enc_payload = signed_request.split(".", 1)
sig_bytes = base64.urlsafe_b64decode(enc_sig + "=" * (-len(enc_sig) % 4))
raw = base64.urlsafe_b64decode(enc_payload + "=" * (-len(enc_payload) % 4))
expected = hmac.new(THREADS_SECRET.encode(), enc_payload.encode("ascii"), hashlib.sha256).digest()
print("Local verify:", hmac.compare_digest(sig_bytes, expected))
print("Decoded payload:", json.loads(raw))

# Now send the SAME signed_request to production
r = httpx.post(
    "https://hudhud-radar.vercel.app/api/data-deletion",
    data={"signed_request": signed_request}, timeout=60,
)
print("Production verify:", r.status_code, r.json())

# Also try WITHOUT stripping padding in the payload (some signers keep it)
payload_b64_padded = base64.urlsafe_b64encode(json.dumps(payload_obj).encode()).decode()
sig2 = hmac.new(THREADS_SECRET.encode(), payload_b64_padded.encode("ascii"), hashlib.sha256).digest()
sr2 = f"{base64.urlsafe_b64encode(sig2).decode().rstrip('=')}.{payload_b64_padded}"
r2 = httpx.post(
    "https://hudhud-radar.vercel.app/api/data-deletion",
    data={"signed_request": sr2}, timeout=60,
)
print("Production verify (padded payload):", r2.status_code, r2.json())

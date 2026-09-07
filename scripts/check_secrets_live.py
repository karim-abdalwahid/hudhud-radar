"""Check deployed secrets metadata (lengths + last4 only)."""
import httpx

s = httpx.Client(timeout=60)
r = s.post(
    "https://hudhud-radar.vercel.app/auth/login",
    json={"email": "karim@ebdamarketing.com", "password": "Hudhud2026!Secure"},
)
print("login:", r.status_code)
r2 = s.get("https://hudhud-radar.vercel.app/api/debug/secrets-check")
print("secrets-check:", r2.status_code)
d = r2.json()
for k, v in d.items():
    if isinstance(v, dict):
        print("  " + k + ": set=" + str(v["set"]) + " len=" + str(v["length"]) + " last4=" + str(v.get("last4", "-")))

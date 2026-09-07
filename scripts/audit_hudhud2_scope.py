"""Audit the hudhud2-scope deployment (canonical domain): what env vars are missing."""
import httpx

BASE = "https://hudhud-radar.vercel.app"
s = httpx.Client(timeout=60)

# Login (Supabase users table is shared → same credentials work)
r = s.post(f"{BASE}/auth/login", json={
    "email": "karim@ebdamarketing.com", "password": "Hudhud2026!Secure"
})
print("login:", r.status_code, r.json() if r.status_code == 200 else r.text[:100])

# Secrets audit
r2 = s.get(f"{BASE}/api/debug/secrets-check")
print("\n=== secrets-check (hudhud2 scope) ===")
if r2.status_code == 200:
    d = r2.json()
    for k, v in d.items():
        if isinstance(v, dict):
            state = "✓ set" if v.get("set") else "❌ MISSING"
            print(f"  {k}: {state} (len={v.get('length', 0)}, last4={v.get('last4', '-')})")
else:
    print("  ", r2.status_code, r2.text[:150])

# Meta status
r3 = s.get(f"{BASE}/api/meta/status")
m = r3.json()
print("\n=== Meta status ===")
print("  configured:", m.get("configured"), "| token_valid:", m.get("token_valid"), "| page:", m.get("page_name"))

# Threads status
r4 = s.get(f"{BASE}/api/threads/status")
print("\n=== Threads status ===")
print(" ", r4.json())

# AI providers
r5 = s.get(f"{BASE}/api/ai/providers")
print("\n=== AI providers ===")
print("  count:", len(r5.json().get("providers", [])))

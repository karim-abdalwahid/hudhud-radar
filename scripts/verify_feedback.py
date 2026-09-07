"""Live verification of all owner feedback fixes (canonical domain)."""
import httpx
import os

BASE = os.environ.get("APP_BASE_URL", "https://hudhud-radar.vercel.app")

r = httpx.get(f"{BASE}/login", timeout=30)
c = r.text
print("1. Wordmark capital H:", "Hudhud" in c)
print("1. Google real flow:", 'location.href = "/auth/google"' in c)
print("1. Placeholder i18n (data-i18n-ph):", "data-i18n-ph" in c)

r2 = httpx.get(f"{BASE}/auth/google", follow_redirects=False, timeout=30)
print("4. Google OAuth start ->", r2.status_code, "→", r2.headers.get("location", "")[:85])

r4 = httpx.get(f"{BASE}/static/i18n.js", timeout=30)
print("5. i18n alert keys:", "dash.alerts_title" in r4.text and "dash.alerts_refresh" in r4.text)

r5 = httpx.get(f"{BASE}/settings", timeout=30, follow_redirects=False)
print("5. settings auth-guard:", r5.status_code == 303)

r6 = httpx.get(f"{BASE}/api/ai/brains", timeout=30)
print("8. client brains (Google 33 models):", len(r6.json().get("brains", [])), "available")

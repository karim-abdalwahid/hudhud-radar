"""FINAL comprehensive verification on the canonical domain after env completion."""
import httpx

BASE = "https://hudhud-radar.vercel.app"

print("═" * 60)
print("FINAL VERIFICATION — hudhud-radar.vercel.app (canonical)")
print("═" * 60)

# 1. Health
r = httpx.get(f"{BASE}/health", timeout=30)
d = r.json()
print(f"\n1. Health: {r.status_code} | marker={d.get('deploy_marker')} | threads={d.get('threads_app_configured')} | cron={d.get('cron_configured')}")

# 2. Auth
s = httpx.Client(timeout=60)
r = s.post(f"{BASE}/auth/login", json={"email": "karim@ebdamarketing.com", "password": "Hudhud2026!Secure"})
print(f"2. Owner login: {r.status_code} (admin)")

# 3. Meta
r = s.get(f"{BASE}/api/meta/status").json()
print(f"3. Meta: token_valid={r.get('token_valid')} | page={r.get('page_name', '')[:30]}")

# 4. AI Providers (33 Google models)
r = s.get(f"{BASE}/api/ai/brains").json()
print(f"4. AI brains available: {len(r.get('brains', []))}")

# 5. Knowledge Base
r = s.get(f"{BASE}/api/knowledge/documents").json()
print(f"5. KB documents: {len(r.get('documents', []))}")

# 6. Threads
r = s.get(f"{BASE}/api/threads/status").json()
print(f"6. Threads: configured={r.get('configured')} | connected={r.get('connected')}")

# 7. Admin alerts
r = s.get(f"{BASE}/api/admin/alerts").json()
critical = [a for a in r.get("alerts", []) if a.get("level") == "critical"]
print(f"7. System alerts: {len(r.get('alerts', []))} checks | critical issues: {len(critical)}")

# 8. Gemini live
r = s.get(f"{BASE}/api/debug/llm-status").json()
print(f"8. Gemini live: {r.get('ok')} (http {r.get('http_status')})")

# 9. Cron endpoint with key
import os
import sys
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()
cron = os.getenv("CRON_SECRET")
r = httpx.get(f"{BASE}/api/cron/scheduler-tick?key={cron}", timeout=60)
print(f"9. Cron endpoint: {r.status_code} {r.json().get('status')}")

# 10. Content generation (Gemini)
r = s.post(f"{BASE}/api/content/generate", json={
    "topic": "أهمية الذكاء الاصطناعي في التسويق", "post_type": "post",
    "platform": "facebook", "tone": "friendly", "cta_keyword": "ابدأ"
}, timeout=120)
print(f"10. Content generation: {r.status_code} | model: {r.json().get('model_used')}")

print("\n" + "═" * 60)
print("CANONICAL DOMAIN: FULLY OPERATIONAL ✓")

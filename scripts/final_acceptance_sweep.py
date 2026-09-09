"""Final production acceptance sweep for the WS0-G build (Entry 034)."""
import httpx

BASE = "https://www.hudhd.com"
checks = []


def check(name, ok):
    checks.append((name, bool(ok)))


# Anonymous probes
r = httpx.get(f"{BASE}/health", timeout=30)
check("health 200", r.status_code == 200)

r = httpx.get(f"{BASE}/terms", timeout=30)
check("terms EN + Egyptian law", r.status_code == 200 and "Arab Republic of Egypt" in r.text)

r = httpx.get(f"{BASE}/terms?lang=ar", timeout=30)
check("terms AR", r.status_code == 200 and "جمهورية مصر العربية" in r.text)

r = httpx.get(f"{BASE}/privacy", timeout=30)
check("privacy EN full", r.status_code == 200 and "AI processing" in r.text)

r = httpx.get(f"{BASE}/login", timeout=30)
check("login EN/LTR default", r.status_code == 200 and 'lang="en" dir="ltr"' in r.text)

r = httpx.get(f"{BASE}/static/favicon.ico", timeout=30)
check("favicon served", r.status_code == 200)

r = httpx.get(f"{BASE}/static/manifest.json", timeout=30)
check("manifest served", r.status_code == 200)

r = httpx.get(f"{BASE}/api/notifications", timeout=30)
check("notifications gated (anon 401)", r.status_code == 401)

r = httpx.get(f"{BASE}/api/admin/users", timeout=30)
check("admin users gated (anon 401)", r.status_code == 401)

r = httpx.get(f"{BASE}/api/knowledge/documents", timeout=30)
check("knowledge gated (anon 401)", r.status_code == 401)

# Admin session probes
s = httpx.Client(base_url=BASE, timeout=30)
lr = s.post(f"{BASE}/auth/login",
            json={"email": "admin.test@hudhud.test", "password": "AdminTest#2026"})
check("admin login", lr.status_code == 200)

r = s.get(f"{BASE}/api/admin/templates")
check("templates list (6 seeded)", r.status_code == 200 and len(r.json().get("templates", [])) >= 6)

r = s.get(f"{BASE}/api/admin/overview")
check("admin overview KPIs", r.status_code == 200)

r = s.get(f"{BASE}/api/admin/users")
check("admin users list", r.status_code == 200)

r = s.get(f"{BASE}/api/notifications")
check("my notifications", r.status_code == 200)

r = s.get(f"{BASE}/users")
check("/users page", r.status_code == 200)

r = s.get(f"{BASE}/templates")
check("/templates page", r.status_code == 200)

r = s.get(f"{BASE}/dashboard")
check("dashboard + sidebar + bell assets", r.status_code == 200 and "/static/saas.js" in r.text)

for name, ok in checks:
    print(("PASS" if ok else "FAIL"), name)
print(f"TOTAL: {sum(1 for _, o in checks if o)}/{len(checks)}")

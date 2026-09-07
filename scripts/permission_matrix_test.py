"""
Phase 3: Full permission matrix test against PRODUCTION.
Tests both roles (admin.test / user.test) across every page + API + bypass attempt.
Produces a pass/fail report.
"""
import json
import sys

import httpx
import os

BASE = os.environ.get("APP_BASE_URL", "https://hudhud-radar.vercel.app")

ADMIN = {"email": "admin.test@hudhud.test", "password": "AdminTest#2026"}
USER = {"email": "user.test@hudhud.test", "password": "UserTest#2026"}


def login(session, creds):
    r = session.post(f"{BASE}/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"login failed: {r.text}"
    return r.json()


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    results.append({"name": name, "status": status, "detail": detail})
    print(f"  [{status}] {name}" + (f" — {detail}" if detail and not condition else ""))


results = []

# ================= Anonymous =================
anon = httpx.Client(timeout=30)
print("=== ANONYMOUS ===")
r = anon.get(f"{BASE}/", timeout=30)
check("GET / (landing) → 200", r.status_code == 200)
r = anon.get(f"{BASE}/login", timeout=30)
check("GET /login → 200", r.status_code == 200)
r = anon.get(f"{BASE}/health", timeout=30)
check("GET /health → 200 (public)", r.status_code == 200)
r = anon.get(f"{BASE}/privacy", timeout=30)
check("GET /privacy → 200", r.status_code == 200)
r = anon.get(f"{BASE}/dashboard", timeout=30, follow_redirects=False)
check("GET /dashboard → 303 redirect", r.status_code == 303, f"got {r.status_code}")
r = anon.get(f"{BASE}/api/leads", timeout=30)
check("GET /api/leads → 401", r.status_code == 401, f"got {r.status_code}")
r = anon.post(f"{BASE}/api/meta/configure", json={"page_id": "123"}, timeout=30)
check("POST /api/meta/configure → 401", r.status_code == 401, f"got {r.status_code}")
r = anon.delete(f"{BASE}/api/knowledge/documents/business_profile.md", timeout=30)
check("DELETE knowledge → 401", r.status_code == 401, f"got {r.status_code}")
r = anon.get(f"{BASE}/api/threads/oauth/authorize", timeout=30)
check("GET threads/authorize → 401", r.status_code == 401, f"got {r.status_code}")

# ================= Admin =================
admin = httpx.Client(timeout=60)
print("=== ADMIN ===")
d = login(admin, ADMIN)
check("admin login → role=admin", d.get("role") == "admin", str(d))
r = admin.get(f"{BASE}/auth/me", timeout=30).json()
check("admin /auth/me authenticated", r.get("authenticated") is True and r.get("role") == "admin")
for page, keyword in [
    ("/dashboard", "Overview"), ("/leads", "Leads"), ("/studio", "Studio"),
    ("/knowledge", "Knowledge"), ("/identity", "Identity"), ("/analytics", "Analytics"),
    ("/settings", "Settings"), ("/automations", "Automations"), ("/inbox", "Inbox"),
]:
    r = admin.get(f"{BASE}{page}", timeout=30)
    check(f"admin GET {page} → 200", r.status_code == 200, f"got {r.status_code}")

for api, method in [
    ("/api/leads", "GET"), ("/api/content/posts", "GET"), ("/api/automations", "GET"),
    ("/api/knowledge/documents", "GET"), ("/api/identity/queue", "GET"),
    ("/api/analytics/summary", "GET"), ("/api/meta/status", "GET"),
    ("/api/inbox/conversations", "GET"), ("/api/threads/status", "GET"),
    ("/api/reports/page-performance", "GET"), ("/api/debug/llm-status", "GET"),
]:
    r = admin.request(method, f"{BASE}{api}", timeout=60)
    check(f"admin {method} {api} → 200", r.status_code == 200, f"got {r.status_code}")

# Admin mutations allowed
r = admin.post(f"{BASE}/api/content/generate", json={
    "topic": "اختبار", "post_type": "post", "platform": "facebook"
}, timeout=90)
check("admin POST content/generate → 200", r.status_code == 200, f"got {r.status_code}")
r = admin.post(f"{BASE}/api/automations", json={
    "name": "perm-test-wf", "platform": "instagram"
}, timeout=30)
check("admin POST automations → 200", r.status_code == 200, f"got {r.status_code}")
test_wf_id = r.json().get("workflow", {}).get("id") if r.status_code == 200 else None

# ================= User (client role) =================
user = httpx.Client(timeout=60)
print("=== USER (non-admin) ===")
d = login(user, USER)
check("user login → role=user", d.get("role") == "user", str(d))
for page in ["/dashboard", "/leads", "/studio", "/knowledge", "/inbox", "/onboarding"]:
    r = user.get(f"{BASE}{page}", timeout=30)
    check(f"user GET {page} → 200 (allowed)", r.status_code == 200, f"got {r.status_code}")
for page in ["/settings", "/identity", "/analytics"]:
    r = user.get(f"{BASE}{page}", timeout=30)
    check(f"user GET {page} → 403 (admin-only)", r.status_code == 403, f"got {r.status_code}")
# Reads allowed for user
r = user.get(f"{BASE}/api/leads", timeout=30)
check("user GET /api/leads → 200", r.status_code == 200, f"got {r.status_code}")
# Mutations blocked for user
r = user.post(f"{BASE}/api/meta/configure", json={"page_id": "999"}, timeout=30)
check("user POST meta/configure → 403", r.status_code == 403, f"got {r.status_code}")
r = user.post(f"{BASE}/api/automations", json={"name": "hack-wf"}, timeout=30)
check("user POST automations → 403", r.status_code == 403, f"got {r.status_code}")
r = user.post(f"{BASE}/api/knowledge/documents", json={"filename": "x.md", "content": "h"}, timeout=30)
check("user POST knowledge → 403", r.status_code == 403, f"got {r.status_code}")
r = user.get(f"{BASE}/api/threads/oauth/authorize", timeout=30)
check("user GET threads/authorize → 403", r.status_code == 403, f"got {r.status_code}")
r = user.post(f"{BASE}/api/content/scheduler/trigger", timeout=30)
check("user POST scheduler/trigger → 403", r.status_code == 403, f"got {r.status_code}")

# Cleanup test workflow
if test_wf_id:
    admin.delete(f"{BASE}/api/automations/{test_wf_id}", timeout=30)

# ================= Summary =================
passed = sum(1 for r in results if r["status"] == "PASS")
failed = [r for r in results if r["status"] == "FAIL"]
print(f"\n{'='*50}")
print(f"PERMISSION MATRIX: {passed}/{len(results)} PASSED")
if failed:
    print("FAILURES:")
    for f in failed:
        print(f"  ✗ {f['name']} — {f['detail']}")
    sys.exit(1)
print("ALL CHECKS PASSED ✓")

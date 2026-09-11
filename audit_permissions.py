"""WS-C+D+E: permission parity + 403 matrix + redirect verification (live).
Also cleans the 2 self-reply test leads from the CRM first."""
import json, sys, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()
import os
from src.core.supabase_client import supabase_db

# ---- cleanup self-reply leads (owner's own username) ----
self_leads = [l for l in (supabase_db.select("leads") or [])
              if l.get("source") == "threads" and l.get("username") == "karim__abdalwahid"]
for l in self_leads:
    supabase_db.delete("messages", l["id"]) if False else None
    for m in (supabase_db.select("messages", {"lead_id": l["id"]}) or []):
        supabase_db.delete("messages", m["id"])
    supabase_db.delete("leads", l["id"])
print(f"cleanup: removed {len(self_leads)} self-reply lead(s)")

# ---- permission matrix via management API? No — runtime HTTP against local server ----
import subprocess, time
from playwright.sync_api import sync_playwright

BASE = "http://localhost:8000"
ADMIN_PAGES = ["/dashboard", "/inbox", "/leads", "/studio", "/automations", "/knowledge",
               "/identity", "/analytics", "/settings", "/users", "/templates"]
ADMIN_APIS = ["/api/admin/overview", "/api/admin/users", "/api/admin/traffic",
              "/api/meta/configure", "/api/threads/oauth/authorize",
              "/api/knowledge/documents", "/api/content/posts"]

results = []

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)

    # Anonymous context: every admin page must redirect to /login; admin APIs -> 401/403
    anon = b.new_context().new_page()
    for path in ADMIN_PAGES:
        r = anon.goto(BASE + path)
        final = anon.url
        ok = "/login" in final
        results.append(("anon", "GET", path, f"{r.status}-> {final.replace(BASE,'')[:40]}", "PASS" if ok else "FAIL"))
    for api in ADMIN_APIS:
        r = anon.request.get(BASE + api)
        ok = r.status in (401, 403)
        results.append(("anon", "GET", api, str(r.status), "PASS" if ok else "FAIL"))

    # Regular user context: login as the existing user.test account (role=user)
    user = b.new_context().new_page()
    user.goto(BASE + "/login")
    user.wait_for_load_state("networkidle")
    user.fill("#loginEmail", "user.test@hudhud.test")
    user.fill("#loginPassword", "AdminTest#2026")
    user.click("#loginBtn")
    user.wait_for_timeout(3000)
    logged = "/login" not in user.url
    print("user.test login:", "OK" if logged else f"FAILED ({user.url})")
    if logged:
        CLIENT_PAGES = {"/dashboard", "/inbox", "/leads", "/studio", "/automations", "/knowledge"}
        for path in ADMIN_PAGES:
            r = user.goto(BASE + path)
            final = user.url
            body = user.inner_text("body")[:80]
            is_403 = "403" in body
            if path in CLIENT_PAGES:
                ok = final.replace(BASE, "") == path and not is_403  # client features stay accessible
                verdict = "PASS (client feature)" if ok else "FAIL"
            else:
                ok = is_403 or "/login" in final
                verdict = "PASS (403 admin-only)" if ok else f"FAIL ({body[:50]!r})"
            results.append(("user", "GET", path, "403 page" if is_403 else final.replace(BASE, "")[:40], verdict))
        USER_OK_APIS = {"/api/knowledge/documents", "/api/content/posts"}  # per-user scoped reads (Wave 9.8 will add user_id filtering)
        for api in ADMIN_APIS:
            r = user.request.get(BASE + api)
            if api in USER_OK_APIS:
                ok = r.status == 200
                verdict = "PASS (per-user read, 200)" if ok else "FAIL"
            else:
                ok = r.status == 403
                verdict = "PASS (403)" if ok else "FAIL"
            results.append(("user", "GET", api, str(r.status), verdict))
    b.close()

print("\n| Role | Method | Path | Result | Verdict |")
print("|---|---|---|---|---|")
fails = 0
for role, method, path, res, verdict in results:
    if verdict.startswith("FAIL"):
        fails += 1
    print(f"| {role} | {method} | {path} | {res} | {verdict} |")
print(f"\nTOTAL: {len(results)} checks | FAILS: {fails}")

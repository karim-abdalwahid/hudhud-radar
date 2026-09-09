"""Final comprehensive acceptance sweep — everything the owner requested."""
import httpx

BASE = "https://www.hudhd.com"
checks = []


def check(name, ok):
    checks.append((name, bool(ok)))


# ── S-Purge: platform is neutral ──────────────────────────────────────────
r = httpx.get(f"{BASE}/terms", timeout=30)
check("Legal: platform operator (no Ebd'a/Karim)", r.status_code == 200
      and "Arab Republic of Egypt" in r.text and "ebdamarketing" not in r.text)

r = httpx.get(f"{BASE}/privacy", timeout=30)
check("Privacy: platform operator + AI disclosure", r.status_code == 200
      and "support@hudhd.com" in r.text and "Gemini" in r.text)

# ── Directions + language (WS-C+D) ────────────────────────────────────────
r = httpx.get(f"{BASE}/login", timeout=30)
check("Auth: EN/LTR default (no Arabic from nowhere)", r.status_code == 200
      and 'lang="en" dir="ltr"' in r.text and '|| "ar"' not in r.text)
check("Auth: row-reverse directions (owner spec)", "flex-direction: row-reverse" in r.text)
check("Auth: consent checkboxes present", 'id="regTerms"' in r.text and 'id="googleTerms"' in r.text)
check("Auth: consent links legal pages", r.text.count('href="/terms"') >= 2)

# ── Brand icons v2 (white bg + full wordmark) ─────────────────────────────
r = httpx.get(f"{BASE}/static/icon-192.png", timeout=30)
check("Brand icon-192 served", r.status_code == 200)
r = httpx.get(f"{BASE}/static/favicon.ico", timeout=30)
check("Favicon served", r.status_code == 200)
r = httpx.get(f"{BASE}/static/manifest.json", timeout=30)
check("Manifest served", r.status_code == 200)

# ── Notifications (WS-F) ──────────────────────────────────────────────────
r = httpx.get(f"{BASE}/api/notifications", timeout=30)
check("Notifications gated (anon 401)", r.status_code == 401)

# ── Admin console (WS-E+H) ────────────────────────────────────────────────
r = httpx.get(f"{BASE}/api/admin/users", timeout=30)
check("Admin users gated (anon 401)", r.status_code == 401)

# ── Honest platform state (S-purge) ───────────────────────────────────────
s = httpx.Client(base_url=BASE, timeout=30)
s.post("/auth/login", json={"email": "admin.test@hudhud.test", "password": "AdminTest#2026"})
r = s.get("/api/meta/status")
d = r.json()
check("Platform honestly disconnected (purge verified)",
      d.get("configured") is False and d.get("token_valid") is False)

r = s.get("/api/admin/overview")
d = r.json()
check("Admin overview: exactly 2 test users, zero fabricated data",
      d.get("users_total") == 2 and d.get("leads_total") == 0)

r = s.get("/api/admin/templates")
check("Templates manager: 6 seeded lifecycle templates",
      r.status_code == 200 and len(r.json().get("templates", [])) >= 6)

r = s.get("/users")
check("/users admin page", r.status_code == 200)

r = s.get("/templates")
check("/templates admin page", r.status_code == 200)

# ── Core health ───────────────────────────────────────────────────────────
r = httpx.get(f"{BASE}/health", timeout=30)
check("Health 200", r.status_code == 200)

for name, ok in checks:
    print(("PASS" if ok else "FAIL"), name)
print(f"TOTAL: {sum(1 for _, o in checks if o)}/{len(checks)}")

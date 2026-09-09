"""
S2 — Production data purge (owner-approved, Entry 035).

The platform was originally built around the owner's own business accounts.
Now it's a neutral SaaS — so ALL personal/business data is purged:

DELETES (personal/business data):
  - app_settings: meta_credentials (owner's page token), threads_credentials,
    meta_cached_posts (owner's posts), system_alerts_cache (stale)
  - kb_documents: business_profile.md (owner's business)
  - content_posts (175 test posts against owner's pages)
  - page_performance_metrics (14 rows — owner's page metrics)
  - activity_logs (175 test/owner rows)
  - notifications (33), site_traffic (1226) — test traffic
  - automations_workflows reset (fabricated defaults)
  - users: ALL except admin.test@hudhud.test + user.test@hudhud.test (kept
    for testing per owner) — includes the owner's personal emails

KEEPS (platform assets): META/THREADS/GOOGLE app credentials (platform apps),
Supabase, Gemini key, CRON_SECRET, APP_BASE_URL.

Usage: python scripts/purge_production_data.py            (dry-run inventory)
       python scripts/purge_production_data.py --apply    (execute)
"""
import json
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent


def env(k):
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith(k + "="):
            return line.split("=", 1)[1].strip()
    return ""


KEEP_USERS = {"admin.test@hudhud.test", "user.test@hudhud.test"}
APP_SETTINGS_DELETE = [
    "meta_credentials", "threads_credentials", "meta_cached_posts",
    "system_alerts_cache", "threads_oauth_states", "google_oauth_states",
]


def main():
    apply = "--apply" in sys.argv
    url = env("SUPABASE_URL").rstrip("/")
    key = env("SUPABASE_SERVICE_ROLE_KEY")
    h = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    results = []

    with httpx.Client(timeout=60) as c:
        def q(sql):
            return c.post(f"https://api.supabase.com/v1/projects/{env('SUPABASE_PROJECT_REF')}/database/query",
                          headers={"Authorization": f"Bearer {env('SUPABASE_MANAGEMENT_TOKEN')}"},
                          json={"query": sql})

        def rest_delete(table, query=""):
            r = c.delete(f"{url}/rest/v1/{table}?{query}", headers=h)
            return r.status_code in (200, 204)

        def count(table):
            r = c.head(f"{url}/rest/v1/{table}", headers={**h, "Prefer": "count=exact"})
            cr = r.headers.get("content-range", "/0")
            return cr.split("/")[-1] if "/" in cr else "?"

        # 1. Users purge (keep test users)
        r = c.get(f"{url}/rest/v1/users?select=id,email", headers=h)
        users = r.json() or []
        to_delete = [u for u in users if u["email"] not in KEEP_USERS]
        results.append(f"users: {len(users)} total, {len(to_delete)} to delete "
                       f"({[u['email'] for u in to_delete]})")
        if apply:
            for u in to_delete:
                c.delete(f"{url}/rest/v1/users?id=eq.{u['id']}", headers=h)
            results.append("  → users purged")

        # 2. app_settings keys
        for k in APP_SETTINGS_DELETE:
            n = count(f"app_settings")  # noqa
            r = c.get(f"{url}/rest/v1/app_settings?key=eq.{k}", headers=h)
            exists = bool(r.json())
            if exists:
                results.append(f"app_settings[{k}]: EXISTS → delete")
                if apply:
                    c.delete(f"{url}/rest/v1/app_settings?key=eq.{k}", headers=h)
                    results.append(f"  → deleted")
            else:
                results.append(f"app_settings[{k}]: not present")

        # 3. business tables (full clear)
        for table in ["content_posts", "page_performance_metrics", "activity_logs",
                      "notifications", "site_traffic", "kb_documents", "leads", "messages"]:
            n = count(table)
            results.append(f"{table}: {n} rows" + (" → purge" if apply and n != "0" else ""))
            if apply and n != "0":
                rest_delete(table)

        # 4. automations workflows reset (neutral empty)
        r = c.get(f"{url}/rest/v1/app_settings?key=eq.automations_workflows", headers=h)
        if r.json():
            if apply:
                c.patch(f"{url}/rest/v1/app_settings?key=eq.automations_workflows",
                        headers=h, json={"value": {"workflows": []}})
                results.append("automations_workflows → reset to empty")
            else:
                results.append("automations_workflows → will reset to empty")

    print("\n".join(results))
    if not apply:
        print("\nDRY-RUN — rerun with --apply to execute the purge.")


if __name__ == "__main__":
    main()

"""S2b cleanup: remove test-stray users created during Phase 9 dev runs
(keeps ONLY admin.test + user.test — same rule as Entry 035)."""
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
KEEP = {"admin.test@hudhud.test", "user.test@hudhud.test"}


def env(k):
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith(k + "="):
            return line.split("=", 1)[1].strip()


def main():
    url, key = env("SUPABASE_URL").rstrip("/"), env("SUPABASE_SERVICE_ROLE_KEY")
    h = {"apikey": key, "Authorization": f"Bearer {key}"}
    with httpx.Client(timeout=30) as c:
        r = c.get(f"{url}/rest/v1/users?select=id,email", headers=h)
        removed = 0
        for u in r.json():
            if u["email"] not in KEEP:
                c.delete(f"{url}/rest/v1/users?id=eq.{u['id']}", headers=h)
                print("removed:", u["email"])
                removed += 1
        # also clear test traffic accumulated by sweeps
        c.delete(f"{url}/rest/v1/site_traffic", headers=h)
        c.delete(f"{url}/rest/v1/activity_logs", headers=h)
        c.delete(f"{url}/rest/v1/notifications", headers=h)
        print(f"users removed: {removed}; traffic/logs/notifications cleared")


if __name__ == "__main__":
    main()

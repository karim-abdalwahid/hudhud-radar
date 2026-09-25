"""Reset admin.test password + verify login (S2b: the purge kept users but
the auth middleware reads from in-memory store on cold start — need to check)."""
import re
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def env(k):
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith(k + "="):
            return line.split("=", 1)[1].strip()


def main():
    raw = (ROOT / ".env").read_text(encoding="utf-8")
    url = re.search(r"SUPABASE_URL=(.+)", raw).group(1).strip()
    key = re.search(r"SUPABASE_SERVICE_ROLE_KEY=(.+)", raw).group(1).strip()
    mgmt = re.search(r"SUPABASE_MANAGEMENT_TOKEN=(.+)", raw).group(1).strip()
    ref = re.search(r"SUPABASE_PROJECT_REF=(.+)", raw).group(1).strip()

    h = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    mh = {"Authorization": f"Bearer {mgmt}", "Content-Type": "application/json"}

    from src.core.auth import hash_password
    new_hash = hash_password("AdminTest#2026")

    with httpx.Client(timeout=60) as c:
        # Check current state
        r = c.post(f"https://api.supabase.com/v1/projects/{ref}/database/query",
                   headers=mh,
                   json={"query": "SELECT id, email, password_hash, is_active FROM users WHERE email = 'admin.test@hudhd.test'"})
        rows = r.json()
        if not rows:
            print("USER NOT FOUND — recreating...")
            r2 = c.post(f"https://api.supabase.com/v1/projects/{ref}/database/query",
                        headers=mh,
                        json={"query": f"INSERT INTO users (email, password_hash, role, is_active, full_name) VALUES ('admin.test@hudhd.test', '{new_hash}', 'admin', true, 'Test Admin') RETURNING id, email"})
            print("recreate:", r2.status_code, r2.json())
        else:
            u = rows[0]
            print("found: email=", u["email"], "| active:", u["is_active"])
            print("hash starts:", u["password_hash"][:40])
            # Update password
            r2 = c.post(f"https://api.supabase.com/v1/projects/{ref}/database/query",
                        headers=mh,
                        json={"query": f"UPDATE users SET password_hash = '{new_hash}' WHERE email = 'admin.test@hudhd.test' RETURNING email"})
            print("password update:", r2.status_code, "OK ✅" if r2.status_code == 200 else r2.text[:200])

        # Verify login via production
        r3 = httpx.post(f"{url}/auth/login",
                        json={"email": "admin.test@hudhd.test", "password": "AdminTest#2026"},
                        headers={"Content-Type": "application/json"}, timeout=30)
        print("login verify:", r3.status_code, "✅" if r3.status_code == 200 else r3.text[:100])

        # Also verify user.test
        r4 = httpx.post(f"{url}/auth/login",
                        json={"email": "user.test@hudhd.test", "password": "UserTest#2026"},
                        headers={"Content-Type": "application/json"}, timeout=30)
        print("user.test login:", r4.status_code, "✅" if r4.status_code == 200 else r4.text[:100])


if __name__ == "__main__":
    main()

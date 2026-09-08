"""Apply migration 005 (terms acceptance columns) to production Supabase."""
import os
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent


def _env(key: str) -> str:
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith(key + "="):
            return line.split("=", 1)[1].strip()
    return os.environ.get(key, "")


def main():
    token = os.environ.get("SUPABASE_MANAGEMENT_TOKEN") or _env("SUPABASE_MANAGEMENT_TOKEN")
    ref = os.environ.get("SUPABASE_PROJECT_REF") or _env("SUPABASE_PROJECT_REF")
    sql = (ROOT / "database" / "migrations" / "005_terms_acceptance.sql").read_text(encoding="utf-8")
    h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    with httpx.Client(timeout=60) as c:
        r = c.post(f"https://api.supabase.com/v1/projects/{ref}/database/query",
                   headers=h, json={"query": sql})
        print("migration 005:", r.status_code, "OK ✅" if r.status_code == 200 else r.text[:300])

        r2 = c.post(f"https://api.supabase.com/v1/projects/{ref}/database/query",
                    headers=h, json={"query": "SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name LIKE 'terms%'"})
        print("verify columns:", r2.text)


if __name__ == "__main__":
    main()

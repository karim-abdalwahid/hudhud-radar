"""Apply migration 010 (per-user isolation columns) to production Supabase."""
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent


def env(k):
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith(k + "="):
            return line.split("=", 1)[1].strip()


def main():
    token, ref = env("SUPABASE_MANAGEMENT_TOKEN"), env("SUPABASE_PROJECT_REF")
    sql = (ROOT / "database" / "migrations" / "010_per_user_isolation.sql").read_text(encoding="utf-8")
    h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    with httpx.Client(timeout=90) as c:
        r = c.post(f"https://api.supabase.com/v1/projects/{ref}/database/query",
                   headers=h, json={"query": sql})
        print("migration 010:", r.status_code, "OK" if r.status_code in (200, 201) else r.text[:400])
        r2 = c.post(f"https://api.supabase.com/v1/projects/{ref}/database/query",
                    headers=h,
                    json={"query": "SELECT table_name, column_name FROM information_schema.columns WHERE column_name='user_id' AND table_name IN ('leads','messages','content_posts','notifications','activity_logs','page_performance_metrics') ORDER BY table_name"})
        print("verify:", r2.text)


if __name__ == "__main__":
    main()

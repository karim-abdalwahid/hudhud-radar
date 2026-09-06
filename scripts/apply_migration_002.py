"""Apply migration 002 via Supabase Management API (idempotent)."""
import sys

import httpx

TOKEN = sys.argv[1] if len(sys.argv) > 1 else ""
REF = "yncxwcvxssvnjffrvxib"
H = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

SQL_FILE = "database/migrations/002_security_hardening_and_pgvector.sql"


def main():
    sql = open(SQL_FILE, encoding="utf-8").read()
    # Split on statement-ending semicolons, keeping COMMENT blocks intact
    statements = [s.strip() for s in sql.split(";") if s.strip() and not s.strip().startswith("--\n")]
    ok = 0
    failed = []
    with httpx.Client(timeout=90) as client:
        for stmt in statements:
            # Skip pure comment blocks
            lines = [l for l in stmt.splitlines() if l.strip() and not l.strip().startswith("--")]
            if not lines:
                continue
            r = client.post(
                f"https://api.supabase.com/v1/projects/{REF}/database/query",
                headers=H,
                json={"query": stmt + ";"},
            )
            first_line = lines[0][:70]
            if r.status_code in (200, 201):
                ok += 1
                print(f"  OK  {first_line}")
            else:
                failed.append(first_line)
                print(f"FAIL  {first_line}: {r.status_code} {r.text[:200]}")
    print(f"\nDone: {ok} succeeded, {len(failed)} failed")
    if failed:
        for f_ in failed:
            print(" -", f_)
        sys.exit(2)


if __name__ == "__main__":
    main()

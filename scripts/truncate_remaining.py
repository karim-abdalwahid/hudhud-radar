"""S2 fix: clear remaining tables via SQL TRUNCATE."""
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent


def env(k):
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith(k + "="):
            return line.split("=", 1)[1].strip()


def main():
    token = env("SUPABASE_MANAGEMENT_TOKEN")
    ref = env("SUPABASE_PROJECT_REF")
    tables = ["content_posts", "page_performance_metrics", "activity_logs",
              "notifications", "site_traffic", "kb_documents", "messages", "leads"]
    h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    sql = "TRUNCATE TABLE " + ", ".join(f"public.{t}" for t in tables) + " CASCADE;"
    with httpx.Client(timeout=60) as c:
        r = c.post(f"https://api.supabase.com/v1/projects/{ref}/database/query",
                   headers=h, json={"query": sql})
        print("TRUNCATE:", r.status_code, "OK" if r.status_code in (200, 201) else r.text[:300])
        for t in tables:
            r2 = c.post(f"https://api.supabase.com/v1/projects/{ref}/database/query",
                        headers=h, json={"query": f"SELECT count(*) FROM public.{t}"})
            print(t, "->", r2.json()[0]["count"] if r2.status_code == 200 else "?")


if __name__ == "__main__":
    main()

"""Verify migration 002 results: anon grants gone, pgvector enabled, indexes exist."""
import httpx

TOKEN = "sbp_fc6bd018f43733b522f2326ecac2b54e8ce20e7f"
REF = "yncxwcvxssvnjffrvxib"
H = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

CHECKS = {
    "remaining_anon_grants": "SELECT table_name, privilege_type FROM information_schema.role_table_grants WHERE table_schema='public' AND grantee='anon' ORDER BY table_name;",
    "pgvector": "SELECT extname FROM pg_extension WHERE extname='vector';",
    "new_indexes": "SELECT indexname FROM pg_indexes WHERE schemaname='public' AND indexname IN ('idx_content_posts_status_sched','idx_content_posts_created','idx_messages_lead_time') ORDER BY indexname;",
}


def main():
    with httpx.Client(timeout=60) as client:
        for name, q in CHECKS.items():
            r = client.post(
                f"https://api.supabase.com/v1/projects/{REF}/database/query",
                headers=H, json={"query": q},
            )
            print(f"{name}: {r.json()}")


if __name__ == "__main__":
    main()

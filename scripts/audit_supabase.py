"""
Comprehensive live Supabase schema audit (Phase 2 of Roadmap v2).
Reads: tables, columns, RLS, policies, grants, FKs, indexes, triggers, extensions.
Outputs a JSON report used to build the audit document + ERD.
"""
import json
import sys

import httpx

TOKEN = sys.argv[1] if len(sys.argv) > 1 else ""
REF = "yncxwcvxssvnjffrvxib"
H = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

QUERIES = {
    "columns": """
        SELECT table_name, column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position;
    """,
    "rls": """
        SELECT relname AS table_name, relrowsecurity AS rls_enabled, relforcerowsecurity AS rls_forced
        FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relkind = 'r'
        ORDER BY relname;
    """,
    "policies": """
        SELECT tablename, policyname, cmd, qual, with_check, roles
        FROM pg_policies WHERE schemaname = 'public'
        ORDER BY tablename, policyname;
    """,
    "grants": """
        SELECT table_name, grantee, string_agg(privilege_type, ',' ORDER BY privilege_type) AS privileges
        FROM information_schema.role_table_grants
        WHERE table_schema = 'public' AND grantee IN ('anon', 'authenticated', 'service_role')
        GROUP BY table_name, grantee
        ORDER BY table_name, grantee;
    """,
    "foreign_keys": """
        SELECT
            tc.table_name AS child_table,
            kcu.column_name AS child_column,
            ccu.table_name AS parent_table,
            ccu.column_name AS parent_column,
            rc.delete_rule
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name
        JOIN information_schema.referential_constraints rc ON tc.constraint_name = rc.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = 'public'
        ORDER BY tc.table_name;
    """,
    "indexes": """
        SELECT tablename, indexname, indexdef
        FROM pg_indexes WHERE schemaname = 'public'
        ORDER BY tablename, indexname;
    """,
    "triggers": """
        SELECT event_object_table AS table_name, trigger_name, action_timing, event_manipulation
        FROM information_schema.triggers
        WHERE trigger_schema = 'public'
        ORDER BY event_object_table;
    """,
    "extensions": "SELECT extname FROM pg_extension ORDER BY extname;",
    "row_counts": """
        SELECT relname AS table_name, n_live_tup AS approx_rows
        FROM pg_stat_user_tables WHERE schemaname = 'public'
        ORDER BY relname;
    """,
    "vector_ready": """
        SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') AS pgvector_installed,
               EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'vector') AS pgvector_available;
    """,
}


def main():
    report = {}
    with httpx.Client(timeout=90) as client:
        for name, query in QUERIES.items():
            r = client.post(
                f"https://api.supabase.com/v1/projects/{REF}/database/query",
                headers=H,
                json={"query": query},
            )
            if r.status_code in (200, 201):
                report[name] = r.json()
                print(f"  OK  {name} ({len(r.json()) if isinstance(r.json(), list) else '?'})")
            else:
                report[name] = {"error": r.text[:300]}
                print(f"FAIL  {name}: {r.status_code}")

    out = sys.argv[2] if len(sys.argv) > 2 else "scratch/supabase_audit.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1, default=str)
    print(f"Saved -> {out}")


if __name__ == "__main__":
    main()

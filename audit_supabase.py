"""
WS-N: Supabase deep audit — tables, RLS, policies, FKs, per-user columns,
payments, knowledge linkage. Read-only via management API SQL.
Output: docs/PROJECT_REPORTS/AUDIT_2026-09-11_SUPABASE.md
"""
import os
import json
import urllib.request
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from dotenv import load_dotenv
load_dotenv()
REF = os.getenv("SUPABASE_PROJECT_REF")
TOK = os.getenv("SUPABASE_MANAGEMENT_TOKEN")
OUT = []
S = lambda s: OUT.append(s)


def sql(query):
    req = urllib.request.Request(
        f"https://api.supabase.com/v1/projects/{REF}/database/query",
        data=json.dumps({"query": query}).encode(), method="POST",
        headers={"Authorization": f"Bearer {TOK}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


S("# 🗄️ Supabase Deep Audit — 2026-09-11\n")

# 1. Tables + RLS status
tables = sql("""
SELECT c.relname AS table, c.relrowsecurity AS rls,
       (SELECT count(*) FROM pg_policy p WHERE p.polrelid = c.oid) AS policies
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relkind = 'r'
ORDER BY c.relname;
""")
S("## 1. Tables & RLS\n")
S("| Table | RLS Enabled | Policies |")
S("|---|---|---|")
no_rls = []
for t in tables:
    S(f"| {t['table']} | {'✅' if t['rls'] else '❌'} | {t['policies']} |")
    if not t["rls"]:
        no_rls.append(t["table"])
S("")
if no_rls:
    S(f"⚠️ **Tables WITHOUT RLS**: {', '.join(no_rls)}\n")
else:
    S("✅ All tables have RLS enabled.\n")

# 2. Per-user columns on business tables
S("## 2. Per-user isolation columns (user_id)\n")
cols = sql("""
SELECT table_name, column_name FROM information_schema.columns
WHERE table_schema='public' AND column_name='user_id'
ORDER BY table_name;
""")
have_uid = {c["table_name"] for c in cols}
expected = ["leads", "messages", "content_posts", "notifications", "activity_logs",
            "page_performance_metrics", "kb_documents", "platform_connections",
            "user_subscriptions", "user_entitlements", "automations_workflows"]
S("| Table | has user_id |")
S("|---|---|")
for t in expected:
    S(f"| {t} | {'✅' if t in have_uid else '❌ MISSING'} |")
S("")

# 3. Foreign keys
S("## 3. Foreign key relationships\n")
fks = sql("""
SELECT tc.table_name AS from_table, kcu.column_name AS from_col,
       ccu.table_name AS to_table
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage ccu ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type='FOREIGN KEY' AND tc.table_schema='public'
ORDER BY tc.table_name;
""")
S("| From | Column | → To |")
S("|---|---|---|")
for f in fks:
    S(f"| {f['from_table']} | {f['from_col']} | {f['to_table']} |")
S("")

# 4. Per-user data counts (owner + test)
S("## 4. Data distribution per user (non-null user_id counts)\n")
for t in ["leads", "messages", "content_posts", "kb_documents", "platform_connections", "user_subscriptions", "user_entitlements"]:
    try:
        rows = sql(f"SELECT user_id, count(*) FROM public.{t} WHERE user_id IS NOT NULL GROUP BY user_id LIMIT 10;")
        nulls = sql(f"SELECT count(*) AS n FROM public.{t} WHERE user_id IS NULL;")
        S(f"- **{t}**: {rows} | NULL user_id rows: {nulls[0]['n']}")
    except Exception as e:
        S(f"- **{t}**: query error {str(e)[:80]}")
S("")

# 5. RLS policy summary (which tables allow only service_role)
S("## 5. Policy names sample (per table)\n")
pols = sql("""
SELECT tablename, policyname, cmd FROM pg_policies WHERE schemaname='public'
ORDER BY tablename LIMIT 60;
""")
S("| Table | Policy | Cmd |")
S("|---|---|---|")
for p in pols:
    S(f"| {p['tablename']} | {p['policyname']} | {p['cmd']} |")

report = "\n".join(OUT)
open("docs/PROJECT_REPORTS/AUDIT_2026-09-11_SUPABASE.md", "w", encoding="utf-8").write(report)
print(report[:4200])

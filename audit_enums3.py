"""Layer 3: every Postgres enum label set vs every Python enum that writes to it."""
import json
import os
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()
from src.leads.models import PlatformSource, SenderType

ref = os.getenv("SUPABASE_PROJECT_REF"); tok = os.getenv("SUPABASE_MANAGEMENT_TOKEN")
def sql(q):
    req = urllib.request.Request(
        f"https://api.supabase.com/v1/projects/{ref}/database/query",
        data=json.dumps({"query": q}).encode(), method="POST",
        headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())

db_enums = {}
for row in sql("SELECT t.typname, e.enumlabel FROM pg_type t JOIN pg_enum e ON e.enumtypid=t.oid WHERE t.typname NOT IN ('aal_level','action','bucket_type','factor_status','factor_type','equality_op','oauth_authorization_status','oauth_client_type','oauth_registration_type','oauth_response_type','one_time_token_type') ORDER BY t.typname"):
    db_enums.setdefault(row["typname"], set()).add(row["enumlabel"])

# map python enums -> the db enum types they write into
checks = {
    "lead_source_enum": [e.value for e in PlatformSource],
    "platform_enum": [e.value for e in PlatformSource] + ["system"],
    "sender_enum": [e.value for e in SenderType],
}
problems = 0
for etype, pyvals in checks.items():
    dbvals = db_enums.get(etype, set())
    missing = [v for v in pyvals if v not in dbvals]
    status = "OK" if not missing else f"MISSING {missing}"
    if missing:
        problems += 1
    print(f"  {etype:<22} py={sorted(pyvals)} db={sorted(dbvals)} -> {status}")

# other enums referenced only as strings in code (activity_status/verification/user_role)
for etype in ("activity_status_enum", "verification_status_enum", "user_role_enum"):
    print(f"  {etype:<22} db={sorted(db_enums.get(etype, set()))}")

# content_posts.status / campaign.status are enum or varchar?
cols = sql("""SELECT table_name, column_name, udt_name FROM information_schema.columns
WHERE table_schema='public' AND column_name IN ('status','platform','source','sender_type','role') ORDER BY table_name""")
enum_cols = [c for c in cols if c["udt_name"] in db_enums]
print("\ncolumns bound to enums:")
for c in enum_cols:
    print(f"  {c['table_name']}.{c['column_name']} -> {c['udt_name']}")
print("\nRESULT:", "ALL ALIGNED ✅" if problems == 0 else f"{problems} ENUM MISALIGNMENTS ❌")

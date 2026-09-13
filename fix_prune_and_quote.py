import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()

# 1. automations _save_db: prune rows removed from memory (source-of-truth fix)
p = "src/automations/service.py"
src = open(p, encoding="utf-8").read()
old = '''        try:
            from src.core.supabase_client import supabase_db
            if not supabase_db.is_connected:
                return False
            now = datetime.now(timezone.utc).isoformat()
            owner = self._owner_user_id()
            for wf in self._workflows.values():'''
if "db_save_workflows(db," not in src:  # method-delegate style exists instead
    pass
# We patch db_save_workflows (pure helper) to also delete removed ids:
old2 = '''    if db is None or not getattr(db, "is_connected", False):
        return False
    now = datetime.now(timezone.utc).isoformat()
    ok = False
    for wf in workflows.values():'''
new2 = '''    if db is None or not getattr(db, "is_connected", False):
        return False
    now = datetime.now(timezone.utc).isoformat()
    ok = False
    # prune rows that no longer exist in the authoritative in-memory set
    try:
        existing = db.select("automations_workflows") or []
        live_ids = set(workflows.keys())
        for row in existing:
            if row.get("id") and row["id"] not in live_ids:
                try:
                    db.delete("automations_workflows", row["id"])
                except Exception as e:
                    logger.warning(f"Automations prune failed for {row['id']}: {e}")
    except Exception as e:
        logger.warning(f"Automations prune check failed: {e}")
    for wf in workflows.values():'''
assert old2 in src, "helper anchor not found"
src = src.replace(old2, new2, 1)
open(p, "w", encoding="utf-8").write(src)
import ast; ast.parse(src)
print("1. db_save_workflows now prunes deleted rows")

# 2. find the quote route real signature
import glob, re
for f in glob.glob("src/modules/billing*/**/*.py", recursive=True) + glob.glob("src/modules/billing*.py"):
    t = open(f, encoding="utf-8").read()
    if "quote" in t:
        for m in re.finditer(r'@router\.get\("([^"]*quote[^"]*)"[^\n]*\nasync def (\w+)\(([^\n]*)', t):
            print("   QUOTE:", m.group(1), "|", m.group(2), "(", m.group(3)[:120])

import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = "tests/test_cron_budget.py"
src = open(p, encoding="utf-8").read()
old = '''    # age it beyond the stuck window
    service.db.update("content_posts", post.id,
                      {"updated_at": (datetime.now(timezone.utc) - timedelta(minutes=20)).isoformat()})'''
new = '''    # age it beyond the stuck window (patch the raw row: the memory-store
    # update() helper always re-stamps updated_at itself)
    for row in service.db.tables["content_posts"]:
        if row["id"] == post.id:
            row["updated_at"] = (datetime.now(timezone.utc) - timedelta(minutes=20)).isoformat()'''
assert old in src
src = src.replace(old, new, 1)
open(p, "w", encoding="utf-8").write(src)
import ast; ast.parse(src)
print("test fixed")

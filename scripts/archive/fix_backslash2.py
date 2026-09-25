import ast
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = "src/modules/inbox_onboarding/__init__.py"
lines = open(p, encoding="utf-8").read().split("\n")

assert lines[199].rstrip().endswith("\\\\"), repr(lines[199][-10:])
lines[199] = '            if (a.get("sender_type") == "lead" and b.get("sender_type") == "agent"'
lines[200] = '                    and "is_conversion_reply" in meta_b'
lines[201] = '                    and not meta_b.get("sent_by") and not meta_b.get("type")'
lines[202] = '                    and a.get("sent_at") and b.get("sent_at")):'
assert lines[213].rstrip().endswith("\\\\"), repr(lines[213][-10:])
lines[213] = '        if (m.get("sender_type") == "agent" and m.get("sent_at")'
lines[214] = '                and isinstance(meta_m, dict) and "is_conversion_reply" in meta_m):'

s = "\n".join(lines)
ast.parse(s)
open(p, "w", encoding="utf-8").write(s)
print("conditions parenthesized + syntax OK")

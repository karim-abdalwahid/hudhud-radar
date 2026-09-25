import ast
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = "src/modules/inbox_onboarding/__init__.py"
s = open(p, encoding="utf-8").read()

# Replace the two multi-line if-conditions (which used backslash continuations
# written literally as '\\') with parenthesized, syntax-safe versions.
old1 = '''            if a.get("sender_type") == "lead" and b.get("sender_type") == "agent" \\
                    and "is_conversion_reply" in meta_b \\
                    and not meta_b.get("sent_by") and not meta_b.get("type") \\
                    and a.get("sent_at") and b.get("sent_at"):'''
new1 = '''            if (a.get("sender_type") == "lead" and b.get("sender_type") == "agent"
                    and "is_conversion_reply" in meta_b
                    and not meta_b.get("sent_by") and not meta_b.get("type")
                    and a.get("sent_at") and b.get("sent_at")):'''
assert old1 in s, "cond1 not found"
s = s.replace(old1, new1, 1)

old2 = '''        if m.get("sender_type") == "agent" and m.get("sent_at") \\
                and isinstance(meta_m, dict) and "is_conversion_reply" in meta_m:'''
new2 = '''        if (m.get("sender_type") == "agent" and m.get("sent_at")
                and isinstance(meta_m, dict) and "is_conversion_reply" in meta_m):'''
assert old2 in s, "cond2 not found"
s = s.replace(old2, new2, 1)

ast.parse(s)
open(p, "w", encoding="utf-8").write(s)
print("conditions parenthesized + syntax OK")

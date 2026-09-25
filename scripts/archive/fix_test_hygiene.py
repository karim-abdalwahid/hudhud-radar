import ast, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = "tests/test_profile_enrichment.py"
src = open(p, encoding="utf-8").read()
old1 = ('orch.resolver.resolve_and_save_lead = MagicMock(\n'
        '        return_value=({"id": "lead_1", "human_takeover": True}, True, None)\n'
        '    )')
new1 = ('monkeypatch.setattr(orch.resolver, "resolve_and_save_lead", MagicMock(\n'
        '        return_value=({"id": "lead_1", "human_takeover": True}, True, None)\n'
        '    ))')
old2 = ('orch.resolver.resolve_and_save_lead = MagicMock(\n'
        '        return_value=({"id": "lead_2", "human_takeover": True}, True, None)\n'
        '    )')
new2 = ('monkeypatch.setattr(orch.resolver, "resolve_and_save_lead", MagicMock(\n'
        '        return_value=({"id": "lead_2", "human_takeover": True}, True, None)\n'
        '    ))')
assert old1 in src and old2 in src, "patterns not found"
src = src.replace(old1, new1).replace(old2, new2)
open(p, "w", encoding="utf-8").write(src)
ast.parse(src)
print("hygiene complete + syntax OK")

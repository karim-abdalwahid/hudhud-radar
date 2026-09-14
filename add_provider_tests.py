import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = "tests/test_audit_fixes.py"
src = open(p, encoding="utf-8").read()
addition = '''

def test_ai_provider_empty_custom_returns_400_not_500(client):
    """Button audit: submitNewProvider() with an empty form must 400 (was 500)."""
    r = client.post("/api/ai/providers", json={"kind": "custom"})
    assert r.status_code == 400, r.text[:200]
    assert "display_name" in r.text or "اسم" in r.text


def test_ai_provider_bad_base_url_returns_400(client):
    r = client.post("/api/ai/providers", json={
        "kind": "custom", "display_name": "X", "base_url": "not-a-url"})
    assert r.status_code == 400, r.text[:200]
'''
src += addition
open(p, "w", encoding="utf-8").write(src)
import ast; ast.parse(src)
print("regression tests appended")

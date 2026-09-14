import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
src = open("src/modules/ai/routes.py", encoding="utf-8").read()
i = src.find("class ProviderCreatePayload")
print(src[i:i+320])
p = "tests/test_audit_fixes.py"
s = open(p, encoding="utf-8").read()
s = s.replace('''    r = client.post("/api/ai/providers", json={"kind": "custom"})
    assert r.status_code == 400, r.text[:200]
    assert "display_name" in r.text or "اسم" in r.text''',
'''    r = client.post("/api/ai/providers",
                    json={"kind": "custom", "provider_key": "",
                          "display_name": "", "base_url": "", "api_key": ""})
    assert r.status_code == 400, r.text[:250]
    assert "display_name" in r.text or "اسم" in r.text''')
s = s.replace('''    r = client.post("/api/ai/providers", json={
        "kind": "custom", "display_name": "X", "base_url": "not-a-url"})
    assert r.status_code == 400, r.text[:200]''',
'''    r = client.post("/api/ai/providers", json={
        "kind": "custom", "provider_key": "bad-url-test",
        "display_name": "X", "base_url": "not-a-url", "api_key": ""})
    assert r.status_code == 400, r.text[:200]''')
open(p, "w", encoding="utf-8").write(s)
import ast; ast.parse(s)
print("tests aligned with payload model")

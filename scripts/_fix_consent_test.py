"""Update consent gate tests: single checkbox controls both paths (owner fix)."""
from pathlib import Path

P = Path("tests/test_consent_gate.py")
c = P.read_text(encoding="utf-8")

c = c.replace(
    "    # google-path checkbox (consent BEFORE the OAuth redirect)\n"
    "    assert 'id=\"googleTerms\"' in r.text\n"
    "    # both link to the legal pages\n"
    "    assert r.text.count('href=\"/terms\"') >= 2\n"
    "    assert r.text.count('href=\"/privacy\"') >= 2",
    "    # single consent checkbox controls BOTH email and Google signup paths\n"
    "    assert 'id=\"googleTerms\"' not in r.text\n"
    "    assert r.text.count('href=\"/terms\"') >= 1\n"
    "    assert r.text.count('href=\"/privacy\"') >= 1"
)

P.write_text(c, encoding="utf-8")
print("test_consent_gate.py updated")

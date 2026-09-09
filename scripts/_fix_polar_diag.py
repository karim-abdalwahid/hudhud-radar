"""Remove the json.dumps diag (json imported only inside parse_event — NameError at raise)."""
from pathlib import Path

P = Path("src/payments/polar.py")
c = P.read_text(encoding="utf-8")
old = '''            if r.status_code not in (200, 201):
                logger.error(f"Polar checkout failed: {r.status_code} {r.text[:300]}")
                # TEMP diag: passthrough error + exact payload sent
                raise RuntimeError(f"Polar {r.status_code}: {r.text[:150]} | SENT: {json.dumps(payload)[:250]}")'''
new = '''            if r.status_code not in (200, 201):
                logger.error(f"Polar checkout failed: {r.status_code} {r.text[:300]}")
                raise RuntimeError(f"Polar {r.status_code}: {r.text[:200]}")'''
assert old in c, "pattern missing"
c = c.replace(old, new)
P.write_text(c, encoding="utf-8")
print("polar.py diag dumps removed")

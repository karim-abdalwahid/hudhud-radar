import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()
import audit_500_hunter as h

res = h.run(raise_exc=False)
bad = [r for r in res if r[2] >= 500]
print(f"cases {len(res)} | 5xx {len(bad)}")
for label, path, code, tb in bad:
    print(f"FAIL [{code}] {label} -> {path}")
    if tb:
        print("     TB:", tb[-320:])

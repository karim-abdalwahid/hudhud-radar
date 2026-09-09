"""Fix literal backtick-n sequences in i18n.js (from a prior PowerShell replace)."""
from pathlib import Path

P = Path("src/templates/static/i18n.js")
c = P.read_text(encoding="utf-8")
c = c.replace('",`n        "', '",\n        "')
P.write_text(c, encoding="utf-8")
print("i18n.js literal backtick-n fixed")

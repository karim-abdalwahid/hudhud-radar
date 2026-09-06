"""Validate settings.html tab structure is balanced."""
import re
from pathlib import Path

t = Path("src/templates/settings.html").read_text(encoding="utf-8")
opens = re.findall(r'id="set-tab-page-(\w+)"', t)
closes = re.findall(r'/set-tab-page-(\w+)', t)
print("Open tabs:", opens)
print("Close tabs:", closes)
print("Balanced:", sorted(opens) == sorted(closes) and len(opens) == 4)

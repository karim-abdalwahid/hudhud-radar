"""Layer 2: settings attribute parity — every settings.NAME used in src must exist
in the Settings model (a missing one = runtime AttributeError = 500)."""
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()
from src.config import Settings

fields = set(Settings.model_fields.keys())

used = {}
for f in Path("src").rglob("*.py"):
    txt = f.read_text(encoding="utf-8", errors="replace")
    for m in re.finditer(r"settings\.([A-Za-z_][A-Za-z0-9_]*)", txt):
        used.setdefault(m.group(1), set()).add(str(f))

missing = {k: v for k, v in used.items() if k not in fields}
print(f"settings fields defined: {len(fields)} | referenced names: {len(used)}")
if missing:
    print(f"\n❌ MISSING on Settings (would 500):")
    for k, files in sorted(missing.items()):
        print(f"  settings.{k}  used in: {', '.join(sorted(files))[:120]}")
else:
    print("✅ all settings.* references exist on the model")

# also: EFFECTIVE_* computed fields defined via @property?
names_in_model = [n for n in dir(Settings) if not n.startswith("_")]
print("\ncomputed/effective attrs:", [n for n in names_in_model if "EFFECTIVE" in n][:5])

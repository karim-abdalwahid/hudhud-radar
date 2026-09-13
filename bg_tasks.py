import re, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
print("=== all background_tasks.add_task call sites ===")
for f in Path("src").rglob("*.py"):
    t = f.read_text(encoding="utf-8", errors="replace")
    for m in re.finditer(r'background_tasks\.add_task\(\s*([^,\)]+)', t):
        fn = m.group(1).strip()
        line = t[:m.start()].count("\n") + 1
        print(f"  {f.name}:{line} -> {fn}")

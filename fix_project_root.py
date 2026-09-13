import ast
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = "src/modules/meta/routes.py"
src = open(p, encoding="utf-8").read()
if "PROJECT_ROOT = " not in src:
    anchor = "from pathlib import Path"
    assert anchor in src
    src = src.replace(anchor,
                      "from pathlib import Path\n\nPROJECT_ROOT = str(Path(__file__).resolve().parents[3])",
                      1)
    open(p, "w", encoding="utf-8").write(src)
ast.parse(src)
import subprocess
r = subprocess.run(["python", "-c",
                    "import sys; sys.path.insert(0, '.');"
                    "from src.modules.meta.routes import PROJECT_ROOT; print('PROJECT_ROOT OK ->', PROJECT_ROOT)"],
                   capture_output=True, text=True)
print(r.stdout.strip() or r.stderr[-300:])

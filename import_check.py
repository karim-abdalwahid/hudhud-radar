import sys, traceback
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()
try:
    import src.automations.service as amod
    print("import OK")
except Exception:
    traceback.print_exc()

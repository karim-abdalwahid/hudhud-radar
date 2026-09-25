import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = "src/meta_api/threads_oauth.py"
src = open(p, encoding="utf-8").read()
i = src.find("def _load_stored_state")
print(src[i:i+650])

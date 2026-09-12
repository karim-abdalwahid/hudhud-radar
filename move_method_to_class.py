import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = "src/meta_api/threads_oauth.py"
src = open(p, encoding="utf-8").read()

start = src.find("\n    # ------------------------------------------------------------------\n    # Proactive refresh (Wave 9.8 cron)")
end = src.find("threads_oauth = ThreadsOAuthManager()")
assert 0 < start < end
block = src[start:end]

# remove from the wrong place
src = src[:start] + "\n\n" + src[end:]

# re-insert inside the class, right before the "Status & disconnect" section
anchor = "    # ------------------------------------------------------------------\n    # Status & disconnect"
assert anchor in src
src = src.replace(anchor, block.strip("\n") + "\n\n" + anchor, 1)

open(p, "w", encoding="utf-8").write(src)
import ast
ast.parse(src)

sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()
import importlib
import src.meta_api.threads_oauth as to
importlib.reload(to)
print("class has refresh_if_expiring:", hasattr(to.ThreadsOAuthManager, "refresh_if_expiring"))

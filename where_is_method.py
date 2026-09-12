import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()
from src.meta_api.threads_oauth import threads_oauth, ThreadsOAuthManager
print("has method:", hasattr(ThreadsOAuthManager, "refresh_if_expiring"))
src = open("src/meta_api/threads_oauth.py", encoding="utf-8").read()
i = src.find("async def refresh_if_expiring")
print("def at offset", i)
print("--- 400 chars BEFORE the def ---")
print(repr(src[max(0, i-400):i]))

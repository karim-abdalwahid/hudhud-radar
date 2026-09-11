"""Reset user.test password to AdminTest#2026 (same mechanism as reset_test_passwords.py)."""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()
from src.core.auth import hash_password
from src.core.supabase_client import supabase_db

rows = supabase_db.select("users", {"email": "user.test@hudhud.test"}) or []
for u in rows:
    r = supabase_db.update("users", u["id"], {"password_hash": hash_password("AdminTest#2026")})
    print(f"reset password for {u['email']} ({u['id'][:8]}):", "OK" if r else "FAILED")

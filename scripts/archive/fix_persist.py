import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = "src/meta_api/threads_oauth.py"
src = open(p, encoding="utf-8").read()
old = '''    def _persist_state(self, state: str, created_at: float):
        self._pending_states[state] = created_at'''
new = '''    def _persist_state(self, state: str, created_at: float):
        """Persists the CSRF state to app_settings — serverless-safe (the
        authorize request and the callback may hit different instances)."""
        self._pending_states[state] = created_at
        try:
            payload = supabase_db.get_setting("threads_oauth_states") or {}
            states = payload.get("states", {}) if isinstance(payload, dict) else {}
            now = time.time()
            states = {s: ts for s, ts in states.items() if now - float(ts) <= 600}
            states[state] = created_at
            supabase_db.set_setting("threads_oauth_states", {"states": states})
        except Exception as e:
            logger.warning(f"OAuth state DB persist failed (memory fallback): {e}")'''
assert old in src
src = src.replace(old, new, 1)
open(p, "w", encoding="utf-8").write(src)
import ast
ast.parse(src)
print("persist aligned to DB structure")

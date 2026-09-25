import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 1. Missing RedirectResponse import (root cause of the 500 on the OAuth callback)
p1 = "src/modules/threads_marketing/routes.py"
src = open(p1, encoding="utf-8").read()
old_imp = "from fastapi import APIRouter, Request, HTTPException, Query, BackgroundTasks, Response, UploadFile, File"
assert old_imp in src
src = src.replace(old_imp,
    old_imp + "\nfrom fastapi.responses import RedirectResponse", 1)
open(p1, "w", encoding="utf-8").write(src)
import ast
ast.parse(src)
print("threads routes: RedirectResponse import added + syntax OK")

# 2. Serverless-safe OAuth state: persist pending states in app_settings (DB)
#    instead of in-memory dict (lost across Vercel instances).
p2 = "src/meta_api/threads_oauth.py"
src2 = open(p2, encoding="utf-8").read()
old_persist = '''    def _persist_state(self, state: str, created_at: float):
        self._pending_states[state] = created_at'''

new_persist = '''    def _persist_state(self, state: str, created_at: float):
        """Persists the CSRF state in app_settings (serverless-safe: the
        authorize request and the callback may hit different instances)."""
        self._pending_states[state] = created_at
        try:
            # prune entries older than 10 minutes, keep the new one
            now = time.time()
            alive = {s: ts for s, ts in self._pending_states.items()
                     if now - ts <= 600 or s == state}
            supabase_db.set_setting("threads_oauth_states", alive)
        except Exception as e:
            logger.warning(f"OAuth state DB persist failed (memory fallback): {e}")'''
assert old_persist in src2
src2 = src2.replace(old_persist, new_persist, 1)

old_load = '''    def _load_stored_state(self, state: str) -> Optional[float]:
        return self._pending_states.get(state)'''
new_load = '''    def _load_stored_state(self, state: str) -> Optional[float]:
        if state in self._pending_states:
            return self._pending_states[state]
        try:
            states = supabase_db.get_setting("threads_oauth_states") or {}
            return states.get(state)
        except Exception:
            return None'''
assert old_load in src2
src2 = src2.replace(old_load, new_load, 1)
open(p2, "w", encoding="utf-8").write(src2)
ast.parse(src2)
print("threads_oauth: DB-backed CSRF state + syntax OK")

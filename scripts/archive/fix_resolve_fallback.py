import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = "src/meta_api/extended_api.py"
src = open(p, encoding="utf-8").read()
old = '''    @staticmethod
    def _resolve_token(user_id: Optional[str] = None) -> Optional[str]:
        """Per-user token (fail-closed entitlement gate) or legacy global."""
        if user_id:
            from src.modules.connections.service import connection_service
            return connection_service.get_active_token(user_id, "threads")
        from src.meta_api.threads_oauth import get_active_threads_token
        return get_active_threads_token()'''
new = '''    @staticmethod
    def _resolve_token(user_id: Optional[str] = None) -> Optional[str]:
        """Per-user token (fail-closed entitlement gate), with legacy global
        fallback while no per-user connections exist (Wave 9.8 interim)."""
        if user_id:
            from src.modules.connections.service import connection_service
            tok = connection_service.get_active_token(user_id, "threads")
            if tok:
                return tok
        from src.meta_api.threads_oauth import get_active_threads_token
        return get_active_threads_token()'''
assert old in src
src = src.replace(old, new, 1)
open(p, "w", encoding="utf-8").write(src)
import ast
ast.parse(src)
print("resolve_token fallback added")

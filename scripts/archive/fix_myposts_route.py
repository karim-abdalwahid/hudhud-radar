import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = "src/modules/threads_marketing/routes.py"
src = open(p, encoding="utf-8").read()
old = '''    from src.meta_api.extended_api import threads_publisher
    return await threads_publisher.get_my_posts(
        limit=limit, user_id=_session_user_id(request) if request else None)'''
new = '''    from src.meta_api.extended_api import threads_leads_sync
    return await threads_leads_sync.get_my_posts(
        limit=limit, user_id=_session_user_id(request) if request else None)'''
assert old in src
src = src.replace(old, new, 1)
open(p, "w", encoding="utf-8").write(src)
import ast
ast.parse(src)
print("route fixed")

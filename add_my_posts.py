import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = "src/modules/threads_marketing/routes.py"
src = open(p, encoding="utf-8").read()

addition = '''

@router.get("/api/threads/my-posts", tags=["Threads"])
async def my_threads_posts(request: Request = None, limit: int = Query(10, ge=1, le=50)):
    """Lists the account's recent published threads (studio Threads manager)."""
    from src.meta_api.extended_api import threads_publisher
    return await threads_publisher.get_my_posts(
        limit=limit, user_id=_session_user_id(request) if request else None)

'''

anchor = '@router.post("/api/threads/sync-replies"'
assert anchor in src
src = src.replace(anchor, addition.lstrip("\n") + "\n" + anchor, 1)
open(p, "w", encoding="utf-8").write(src)
import ast
ast.parse(src)
print("my-posts endpoint added")

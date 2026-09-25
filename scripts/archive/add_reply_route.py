import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = "src/modules/threads_marketing/routes.py"
src = open(p, encoding="utf-8").read()

addition = '''

@router.post("/api/threads/{thread_id}/reply", tags=["Threads"])
async def reply_to_threads_post(thread_id: str, payload: ThreadsPublishPayload,
                                request: Request = None):
    """Replies to a Threads post/reply on behalf of the connected account
    (threads_manage_replies write path). Admin-only; requires the session user's
    per-user connection (or the legacy token fallback)."""
    session_user = _session_user_id(request) if request else None
    from src.core.auth import verify_session_token, SESSION_COOKIE_NAME
    session = verify_session_token(request.cookies.get(SESSION_COOKIE_NAME) or "") if request else None
    if not session or session.get("role") != "admin":
        raise HTTPException(status_code=403, detail="صلاحيات المدير مطلوبة")

    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="نص الرد فارغ")

    token = threads_publisher._resolve_token(session_user)
    if not token:
        raise HTTPException(status_code=400, detail="Threads غير مربوط")

    import httpx as _httpx
    from src.config import settings as _s
    async with _httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(
            f"{_s.THREADS_BASE_URL}/{thread_id}/replies",
            params={"text": payload.text, "access_token": token},
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Threads reply failed: {resp.text[:250]}")
    return {"status": "success", "reply": resp.json()}
'''

anchor = '@router.get("/api/threads/my-posts"'
assert anchor in src
src = src.replace(anchor, addition.lstrip("\n") + "\n" + anchor, 1)
open(p, "w", encoding="utf-8").write(src)
import ast
ast.parse(src)
print("reply route added")

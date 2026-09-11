import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = "src/modules/threads_marketing/routes.py"
src = open(p, encoding="utf-8").read()

# Replace the wrong /replies POST flow with the official container flow
old = '''    import httpx as _httpx
    from src.config import settings as _s
    async with _httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(
            f"{_s.THREADS_BASE_URL}/{thread_id}/replies",
            params={"text": payload.text, "access_token": token},
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Threads reply failed: {resp.text[:250]}")
    return {"status": "success", "reply": resp.json()}'''
new = '''    # Official Threads reply flow: container with reply_to_id -> threads_publish
    # (POST /{id}/replies is not a valid publish endpoint — THApiException 100/33)
    from src.meta_api.extended_api import threads_publisher
    result = await threads_publisher.publish_thread(
        payload.text, reply_to_id=thread_id, user_id=session_user)
    if result.get("status") != "success":
        raise HTTPException(status_code=502, detail=f"Threads reply failed: {result.get('detail', '')[:250]}")
    return {"status": "success", "reply": result}'''
assert old in src
src = src.replace(old, new, 1)
open(p, "w", encoding="utf-8").write(src)

# publish_thread gains reply_to_id support
p2 = "src/meta_api/extended_api.py"
src2 = open(p2, encoding="utf-8").read()
old2 = '''    async def publish_thread(self, text: str, link: Optional[str] = None,
                             user_id: Optional[str] = None) -> Dict[str, Any]:
        token = self._resolve_token(user_id)'''
new2 = '''    async def publish_thread(self, text: str, link: Optional[str] = None,
                             user_id: Optional[str] = None,
                             reply_to_id: Optional[str] = None) -> Dict[str, Any]:
        token = self._resolve_token(user_id)'''
assert old2 in src2
src2 = src2.replace(old2, new2, 1)

old3 = '''            create = await client.post(
                f"{settings.THREADS_BASE_URL}/me/threads",
                data={"media_type": "TEXT", "text": full_text[:500], "access_token": token},
            )'''
new3 = '''            container_data = {"media_type": "TEXT", "text": full_text[:500],
                              "access_token": token}
            if reply_to_id:
                container_data["reply_to_id"] = reply_to_id
            create = await client.post(
                f"{settings.THREADS_BASE_URL}/me/threads",
                data=container_data,
            )'''
assert old3 in src2
src2 = src2.replace(old3, new3, 1)
open(p2, "w", encoding="utf-8").write(src2)

import ast
ast.parse(open(p, encoding="utf-8").read())
ast.parse(open(p2, encoding="utf-8").read())
print("reply route -> official container flow + publish_thread(reply_to_id) + syntax OK")

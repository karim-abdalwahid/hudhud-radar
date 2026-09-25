import ast, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

addition = '''

# --------------------------------------------------------------------
# AI Pause (Wave 9.8 - owner request): per-user master switch silencing
# the autonomous AI across all conversations and automations.
# --------------------------------------------------------------------
class AIPausePayload(BaseModel):
    paused: bool


def _session(request: Request):
    from src.core.auth import verify_session_token, SESSION_COOKIE_NAME
    session = verify_session_token(request.cookies.get(SESSION_COOKIE_NAME) or "")
    if not session or not session.get("sub"):
        raise HTTPException(status_code=401, detail="غير مصرح - يرجى تسجيل الدخول")
    return session


@router.get("/api/ai/pause", tags=["AI Control"])
async def get_ai_pause(request: Request):
    """Returns the session user's AI pause state (user + global + effective)."""
    session = _session(request)
    from src.ai.pause import pause_status
    return {"status": "success", **pause_status(session["sub"], session.get("role") == "admin")}


@router.post("/api/ai/pause", tags=["AI Control"])
async def set_ai_pause(payload: AIPausePayload, request: Request):
    """
    Toggles the user's AI master switch. Admins also control the global
    legacy-operation switch (the env-connected pages have no per-lead owner).
    Effective semantics: global OR user flag silences ALL autonomous AI
    (messages + comment automations). Human Takeover stays per-conversation.
    """
    session = _session(request)
    from src.ai.pause import set_ai_pause as _set, pause_status
    res = _set(payload.paused, session["sub"], session.get("role") == "admin")
    return {"status": "success", **res, **pause_status(session["sub"], session.get("role") == "admin")}
'''
with open("src/modules/ai/routes.py", "a", encoding="utf-8") as f:
    f.write(addition)
ast.parse(open("src/modules/ai/routes.py", encoding="utf-8").read())
print("routes appended + syntax OK")

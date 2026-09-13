"""Phase 5 fixes for the two 500s (backend-only, zero UI impact):
1. meta routes: import Path (NameError on every configure).
2. knowledge create/update: validation errors -> clean 400 (was 500)."""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 1. Path import in meta routes
p = "src/modules/meta/routes.py"
src = open(p, encoding="utf-8").read()
if "from pathlib import Path" not in src:
    anchor = "from fastapi import APIRouter"
    assert anchor in src
    src = src.replace(anchor, "from pathlib import Path\n" + anchor, 1)
    open(p, "w", encoding="utf-8").write(src)
    print("1. meta routes: Path imported")
import ast; ast.parse(src)

# where is Path actually used? confirm
i = src.find("Path(")
print("   first Path() usage at:", src[max(0, i-60):i+80].replace("\n", " | ")[:120])

# 2. knowledge create/update ValueError -> 400
p2 = "src/modules/knowledge/routes.py"
s2 = open(p2, encoding="utf-8").read()
old_create = '''@router.post("/api/knowledge/documents", tags=["Knowledge Base & RAG"])
async def create_knowledge_document(payload: CreateDocumentRequest, request: Request):
    """Creates a new knowledge document owned by the session user."""
    res = db_knowledge_base.save_document(payload.filename, payload.content,
                                          user_id=_session_user(request))
    knowledge_base.reload()
    return res'''
new_create = '''@router.post("/api/knowledge/documents", tags=["Knowledge Base & RAG"])
async def create_knowledge_document(payload: CreateDocumentRequest, request: Request):
    """Creates a new knowledge document owned by the session user."""
    try:
        res = db_knowledge_base.save_document(payload.filename, payload.content,
                                              user_id=_session_user(request))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    knowledge_base.reload()
    return res'''
assert old_create in s2
s2 = s2.replace(old_create, new_create, 1)

old_upd = '''    """Updates a knowledge document (owner-scoped) and hot-reloads the AI agent's memory."""
    res = db_knowledge_base.save_document(filename, payload.content,
                                          user_id=_session_user(request))'''
new_upd = '''    """Updates a knowledge document (owner-scoped) and hot-reloads the AI agent's memory."""
    try:
        res = db_knowledge_base.save_document(filename, payload.content,
                                              user_id=_session_user(request))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))'''
assert old_upd in s2
s2 = s2.replace(old_upd, new_upd, 1)
open(p2, "w", encoding="utf-8").write(s2)
ast.parse(s2)
print("2. knowledge routes: ValueError -> 400")

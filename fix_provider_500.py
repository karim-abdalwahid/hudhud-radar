import ast, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ---- 1. manager: validate custom provider inputs (fail early with ValueError) ----
p = "src/ai/provider_manager.py"
src = open(p, encoding="utf-8").read()
old = '''        else:
            key = key or f"custom-{int(time.time())}"
            row = {
                "kind": "custom",
                "provider_key": key,
                "displ'''
i = src.find(old)
assert i > 0, "custom branch anchor not found"
# show what follows to craft the injection precisely
seg = src[i:i+700]
anchor2 = 'key = key or f"custom-{int(time.time())}"'
assert anchor2 in src
src = src.replace(anchor2, anchor2 + '''
            base = (payload.get("base_url") or "").strip()
            disp = (payload.get("display_name") or "").strip()
            if not disp:
                raise ValueError("اسم المزود مطلوب / display_name is required")
            if not base.startswith("http"):
                raise ValueError("رابط Base URL غير صالح — يجب أن يبدأ بـ https://")''', 1)
open(p, "w", encoding="utf-8").write(src)
ast.parse(src)
print("1. custom provider validation added")

# ---- 2. route: never 500 on sync failure after a successful create ----
p2 = "src/modules/ai/routes.py"
s2 = open(p2, encoding="utf-8").read()
old_route = '''    try:
        res = ai_provider_manager.create_provider(payload.model_dump())
        # Auto-discover immediately
        sync = ai_provider_manager.sync_provider_models(res["provider_id"])
        return {"status": "success", **res, "sync": {k: v for k, v in sync.items() if k != "models"}}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=_safe_error(e))'''
new_route = '''    try:
        res = ai_provider_manager.create_provider(payload.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=_safe_error(e))
    # Auto-discover — a sync failure must NOT 500 a successful creation
    try:
        sync = ai_provider_manager.sync_provider_models(res["provider_id"])
        sync_out = {k: v for k, v in sync.items() if k != "models"}
    except Exception as e:
        logger.warning(f"provider auto-sync failed after create: {e}")
        sync_out = {"status": "error", "detail": "sync failed — models can be synced later"}
    return {"status": "success", **res, "sync": sync_out}'''
assert old_route in s2
s2 = s2.replace(old_route, new_route, 1)
open(p2, "w", encoding="utf-8").write(s2)
ast.parse(s2)
print("2. create-provider route hardened (no 500 after create)")

# ---- 3. restore leftover takeover flag on the old seed test lead ----
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()
from src.core.supabase_client import supabase_db
for l in (supabase_db.select("leads", {"instagram_account_id": "user_999"}) or []):
    if l.get("human_takeover"):
        supabase_db.update("leads", l["id"], {"human_takeover": False})
        print("3. restored human_takeover=False on seed lead", l["id"][:8])
else:
    print("3. no stale takeover flags on seed lead")

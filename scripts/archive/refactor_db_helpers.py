import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = "src/automations/service.py"
src = open(p, encoding="utf-8").read()

# 1. Insert module-level pure DB functions before the class definition
anchor = "class AutomationsService:"
funcs = '''# ----------------------------------------------------------------------
# Wave 9.8: automations_workflows table (source of truth) — pure helpers
# (db injected for testability; class methods delegate to these).
# ----------------------------------------------------------------------
def db_load_workflows(db) -> Optional[List[Workflow]]:
    """Rebuilds workflows from table rows (config JSONB = full model dump).
    Returns None when unavailable/empty (caller falls back to legacy stores)."""
    if db is None or not getattr(db, "is_connected", False):
        return None
    try:
        rows = db.select("automations_workflows") or []
        if not rows:
            return None
        wfs: List[Workflow] = []
        for r in rows:
            cfg = r.get("config") or {}
            try:
                wfs.append(Workflow(**cfg))
            except Exception as e:
                logger.warning(f"Skipping malformed automation row {r.get('id')}: {e}")
        return wfs or None
    except Exception as e:
        logger.warning(f"Automations DB load failed (legacy fallback): {e}")
        return None


def db_save_workflows(db, workflows: Dict[str, "Workflow"],
                      owner_user_id: Optional[str] = None) -> bool:
    """Upserts each workflow (column subset for querying + full model in
    config JSONB). Best-effort: per-row failures are logged, never raised."""
    if db is None or not getattr(db, "is_connected", False):
        return False
    now = datetime.now(timezone.utc).isoformat()
    ok = False
    for wf in workflows.values():
        payload = {
            "id": wf.id,
            "name": wf.name,
            "platform": wf.platform,
            "status": wf.status,
            "keywords": wf.keywords or [],
            "target_type": wf.target_type,
            "target_post_id": wf.target_post_id,
            "like_comment": wf.like_comment,
            "reply_comment": wf.reply_comment,
            "reply_comment_text": wf.reply_comment_text,
            "send_dm": wf.send_dm,
            "dm_text": wf.dm_text,
            "last_executed_at": getattr(wf, "last_executed_at", None),
            "execution_count": getattr(wf, "execution_count", 0) or 0,
            "config": wf.model_dump(mode="json"),
            "updated_at": now,
        }
        if owner_user_id:
            payload["user_id"] = owner_user_id
        try:
            existing = db.select("automations_workflows", {"id": wf.id}) or []
            if existing:
                db.update("automations_workflows", wf.id, payload)
            else:
                db.insert("automations_workflows", payload)
            ok = True
        except Exception as e:
            logger.warning(f"Automations DB upsert failed for {wf.id}: {e}")
    return ok


'''
assert anchor in src
src = src.replace(anchor, funcs + anchor, 1)

# 2. Replace the earlier method bodies with thin delegates (drop the previous
#    _owner_user_id/_load_db/_save_db block and re-delegate)
start = src.find("    def _owner_user_id(self)")
end = src.find("    def _load_supabase(self)")
assert 0 < start < end
delegates = '''    def _owner_user_id(self) -> Optional[str]:
        """Stamp rows with the legacy workspace operator (oldest admin)."""
        try:
            if not getattr(self, "_owner_cache", None):
                from src.core.supabase_client import supabase_db
                rows = supabase_db.select("users", {"role": "admin"}) or []
                if rows:
                    self._owner_cache = sorted(
                        rows, key=lambda u: u.get("created_at") or "")[0]["id"]
            return getattr(self, "_owner_cache", None)
        except Exception:
            return None

    def _load_db(self) -> Optional[List[Workflow]]:
        from src.core.supabase_client import supabase_db
        return db_load_workflows(supabase_db)

    def _save_db(self) -> bool:
        from src.core.supabase_client import supabase_db
        return db_save_workflows(supabase_db, self._workflows, self._owner_user_id())

'''
src = src[:start] + delegates + src[end:]
open(p, "w", encoding="utf-8").write(src)
import ast; ast.parse(src)
print("pure helpers + delegates in place")

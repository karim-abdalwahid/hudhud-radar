import sys, json
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 1. cron endpoint
p = "src/modules/cron_admin/routes.py"
src = open(p, encoding="utf-8").read()
if "/api/cron/threads-token-refresh" not in src:
    addition = '''

@router.get("/api/cron/threads-token-refresh", tags=["Cron"])
async def cron_threads_token_refresh(request: Request):
    """Daily (Wave 9.8): refresh Threads tokens — legacy + per-user — that
    expire within 7 days. Failures are logged, never raised."""
    _verify_cron_secret(request)
    result = await threads_oauth_manager.refresh_if_expiring()
    if result.get("refreshed"):
        from src.modules.notifications.hooks import _notify_admin
        _notify_admin("🔄 تحديث توكن Threads",
                      f"تم تحديث {len(result['refreshed'])} توكن(ات) قبل انتهائها",
                      "success", {"job": "threads_token_refresh", **result})
    return result
'''
    src += addition
    open(p, "w", encoding="utf-8").write(src)
    import ast; ast.parse(src)
    print("cron threads-token-refresh endpoint added")
else:
    print("cron endpoint already present")

# 2. vercel.json cron (daily 04:00 — scheduler-tick stays 03:00)
vp = "vercel.json"
cfg = json.loads(open(vp, encoding="utf-8").read())
crons = cfg.setdefault("crons", [])
if not any(c.get("path") == "/api/cron/threads-token-refresh" for c in crons):
    crons.append({"path": "/api/cron/threads-token-refresh", "schedule": "0 4 * * *"})
    json.dump(cfg, open(vp, "w", encoding="utf-8"), indent=2)
    print("vercel.json cron added")
else:
    print("vercel cron already present")

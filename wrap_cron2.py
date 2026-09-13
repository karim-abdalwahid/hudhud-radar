import ast, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = "src/modules/cron_admin/routes.py"
src = open(p, encoding="utf-8").read()

old1 = '''    _verify_cron_secret(request)
    result = await meta_insights_sync.sync_recent_metrics(days=7)
    from src.modules.notifications.hooks import notify_sync_result
    notify_sync_result("insights", result)
    return result'''
new1 = '''    _verify_cron_secret(request)
    try:
        result = await meta_insights_sync.sync_recent_metrics(days=7)
    except Exception as e:
        logger.error(f"insights sync cron failed (reported 200): {e}")
        return {"status": "partial", "error": str(e)[:200]}
    from src.modules.notifications.hooks import notify_sync_result
    try:
        notify_sync_result("insights", result)
    except Exception as e:
        logger.warning(f"insights notify failed: {e}")
    return result'''
assert old1 in src
src = src.replace(old1, new1, 1)

old2 = '''    _verify_cron_secret(request)
    result = await threads_oauth_manager.refresh_if_expiring()
    if result.get("refreshed"):'''
new2 = '''    _verify_cron_secret(request)
    try:
        result = await threads_oauth_manager.refresh_if_expiring()
    except Exception as e:
        logger.error(f"threads token-refresh cron failed (reported 200): {e}")
        return {"status": "partial", "error": str(e)[:200]}
    if result.get("refreshed"):'''
assert old2 in src
src = src.replace(old2, new2, 1)

open(p, "w", encoding="utf-8").write(src)
ast.parse(src)
print("both cron endpoints now always-200")

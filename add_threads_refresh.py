import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = "src/meta_api/threads_oauth.py"
src = open(p, encoding="utf-8").read()

addition = '''
    # ------------------------------------------------------------------
    # Proactive refresh (Wave 9.8 cron): refresh any Threads token — legacy
    # global or per-user connections — expiring within 7 days.
    # ------------------------------------------------------------------
    async def refresh_if_expiring(self, days_threshold: int = 7) -> Dict[str, Any]:
        from datetime import datetime, timedelta
        refreshed, failed = [], []
        cutoff = time.time() + days_threshold * 86400

        # 1) Legacy global token
        creds = _get_stored_creds()
        exp = creds.get("expires_at") or 0
        if creds.get("access_token") and exp and exp < cutoff:
            res = await self.refresh_token()
            (refreshed if res.get("status") == "success" else failed).append("legacy")

        # 2) Per-user platform_connections (threads)
        try:
            rows = supabase_db.select("platform_connections",
                                      {"platform": "threads", "status": "active"}) or []
        except Exception:
            rows = []
        for r in rows:
            exp_s = r.get("token_expires_at")
            try:
                exp_dt = datetime.fromisoformat(str(exp_s).replace("Z", "+00:00")) if exp_s else None
            except Exception:
                exp_dt = None
            if not exp_dt or exp_dt.timestamp() >= cutoff:
                continue
            try:
                from src.core.crypto import decrypt_token, encrypt_token
                tok = decrypt_token(r.get("access_token_encrypted") or "")
                if not tok:
                    continue
                async with httpx.AsyncClient(timeout=20.0) as client:
                    resp = await client.get(
                        f"{THREADS_GRAPH_BASE}/refresh_access_token",
                        params={"grant_type": "th_refresh_token", "access_token": tok},
                    )
                if resp.status_code != 200:
                    failed.append(str(r.get("user_id"))[:8])
                    logger.warning(f"Threads per-user refresh failed for {str(r.get('user_id'))[:8]}: {resp.status_code}")
                    continue
                data = resp.json()
                new_exp = datetime.now(timezone.utc) + timedelta(
                    seconds=int(data.get("expires_in", 5184000)))
                updates = {
                    "access_token_encrypted": encrypt_token(data.get("access_token")),
                    "token_expires_at": new_exp.isoformat(),
                }
                if data.get("refresh_token"):
                    md = dict(r.get("metadata") or {})
                    md["refresh_token_encrypted"] = encrypt_token(data["refresh_token"])
                    updates["metadata"] = md
                supabase_db.update("platform_connections", r["id"], updates)
                refreshed.append(str(r.get("user_id"))[:8])
                logger.info(f"Threads per-user token refreshed for {str(r.get('user_id'))[:8]}")
            except Exception as e:
                failed.append(str(r.get("user_id"))[:8])
                logger.warning(f"Threads per-user refresh error for {str(r.get('user_id'))[:8]}: {e}")

        return {"status": "success", "refreshed": refreshed, "failed": failed}

'''

anchor = "threads_oauth = ThreadsOAuthManager()"
assert anchor in src
src = src.replace(anchor, addition + anchor, 1)
open(p, "w", encoding="utf-8").write(src)
import ast; ast.parse(src)
print("refresh_if_expiring added to ThreadsOAuthManager")

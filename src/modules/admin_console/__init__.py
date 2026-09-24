"""
Admin Console module (WS-E+H) — owner-only management surfaces:

  GET  /api/admin/users            list (search, filter) + per-user stats
  PATCH /api/admin/users/{id}      edit profile / activate-deactivate / role
  POST /api/admin/users/{id}/credits   grant AI credits (owner requirement)
  POST /api/admin/users/{id}/plan      set plan manually (pre-Phase 9)
  GET  /api/admin/overview         KPIs: users, signups-7d, traffic, AI usage
  GET  /api/admin/traffic          recent page-view log

Traffic collection: middleware hook (lightweight internal log, no tracking
cookies — disclosed in the Privacy Policy, section 9 Cookies).
"""
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

from src.core.auth import verify_session_token, SESSION_COOKIE_NAME
from src.core.logger import logger
from src.core.modules import module_registry
from src.core.supabase_client import supabase_db


class AdminUserUpdatePayload(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[str] = None


class CreditsPayload(BaseModel):
    amount: int            # may be negative? No — grants only; use plan switch for resets
    note: Optional[str] = None


class PlanPayload(BaseModel):
    plan: str              # free | starter | growth | scale


def _require_admin(request: Request) -> Dict:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    session = verify_session_token(token) if token else None
    if not session or session.get("role") != "admin":
        raise HTTPException(status_code=403, detail="هذه العملية تتطلب صلاحيات المدير")
    return session


def register(app: FastAPI) -> None:
    @app.get("/api/admin/users", tags=["Admin Console"])
    async def list_users(request: Request, search: str = "", limit: int = 50):
        _require_admin(request)
        users = supabase_db.select("users") or []
        if search:
            s = search.strip().lower()
            users = [u for u in users if s in (u.get("email") or "").lower()
                     or s in (u.get("full_name") or "").lower()]
        users.sort(key=lambda u: u.get("created_at") or "", reverse=True)
        # per-user counts for context
        leads = supabase_db.select("leads") or []
        lead_counts = {}
        for l in leads:
            lead_counts[l.get("id")] = lead_counts.get(l.get("id"), 0) + 1
        out = []
        for u in users[:min(max(limit, 1), 200)]:
            out.append({
                "id": u.get("id"),
                "email": u.get("email"),
                "full_name": u.get("full_name"),
                "phone": u.get("phone"),
                "role": u.get("role"),
                "is_active": u.get("is_active"),
                "plan": u.get("plan", "free"),
                "ai_credits": u.get("ai_credits", 100),
                "terms_accepted_at": u.get("terms_accepted_at"),
                "created_at": u.get("created_at"),
                "last_login_at": u.get("last_login_at"),
                "leads_count": lead_counts.get(u.get("id"), 0),
            })
        return {"status": "success", "count": len(out), "users": out}

    @app.patch("/api/admin/users/{user_id}", tags=["Admin Console"])
    async def update_user(user_id: str, payload: AdminUserUpdatePayload, request: Request):
        session = _require_admin(request)
        user = supabase_db.select("users", {"id": user_id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if user[0].get("id") == session.get("sub") and payload.is_active is False:
            raise HTTPException(status_code=400, detail="لا يمكنك تعطيل حسابك أنت")
        if payload.role and payload.role not in ("admin", "user"):
            raise HTTPException(status_code=400, detail="role غير صالح")
        updates = {k: v for k, v in payload.model_dump().items() if v is not None}
        if not updates:
            raise HTTPException(status_code=400, detail="لا يوجد شيء للتحديث")
        updated = supabase_db.update("users", user_id, updates)
        return {"status": "success", "user": updated}

    @app.post("/api/admin/users/{user_id}/credits", tags=["Admin Console"])
    async def grant_credits(user_id: str, payload: CreditsPayload, request: Request):
        _require_admin(request)
        if payload.amount <= 0:
            raise HTTPException(status_code=400, detail="المبلغ يجب أن يكون رقماً موجباً")
        users = supabase_db.select("users", {"id": user_id})
        if not users:
            raise HTTPException(status_code=404, detail="User not found")
        current = int(users[0].get("ai_credits") or 0)
        new_total = current + payload.amount
        updated = supabase_db.update("users", user_id, {"ai_credits": new_total})
        try:
            supabase_db.insert("usage_events", {
                "user_id": user_id,
                "kind": "admin_grant",
                "amount": payload.amount,
                "meta": {"note": payload.note or "Admin grant", "previous": current, "new": new_total},
            })
        except Exception as e:
            logger.warning(f"usage_events insert failed for admin grant: {e}")
        try:
            from src.modules.notifications.service import notification_service
            title_ar = f"⚡ تم إضافة {payload.amount} رصيد ردود ذكية"
            body_ar = f"تمت إضافة الرصيد إلى حسابك بنجاح. رصيدك الإجمالي الآن: {new_total} نقطة."
            title_en = f"⚡ Added {payload.amount} AI credits"
            body_en = f"Credits successfully added to your account. Your new total: {new_total} points."
            notification_service.create(
                user_id,
                title_ar,
                body_ar,
                "success",
                {
                    "job": "credits_grant",
                    "amount": payload.amount,
                    "title_ar": title_ar,
                    "body_ar": body_ar,
                    "title_en": title_en,
                    "body_en": body_en,
                },
            )
        except Exception:
            pass
        return {
            "status": "success",
            "ai_credits": (updated or {}).get("ai_credits", new_total),
            "granted": payload.amount,
            "note": payload.note,
        }

    @app.post("/api/admin/users/{user_id}/plan", tags=["Admin Console"])
    async def set_plan(user_id: str, payload: PlanPayload, request: Request):
        _require_admin(request)
        if payload.plan not in ("free", "starter", "growth", "scale"):
            raise HTTPException(status_code=400, detail="خطة غير معروفة")
        from src.modules.billing.services import entitlement_service
        sub_status = entitlement_service.apply_plan(user_id, payload.plan)
        return {
            "status": "success",
            "plan": payload.plan,
            "subscription": sub_status,
        }

    @app.get("/api/admin/overview", tags=["Admin Console"])
    async def admin_overview(request: Request):
        _require_admin(request)
        users = supabase_db.select("users") or []
        traffic = supabase_db.select("site_traffic") or []
        logs = supabase_db.select("activity_logs") or []
        leads = supabase_db.select("leads") or []
        now_iso = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
        week = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).__class__.fromisoformat(now_iso[:10])
        signups_7d = sum(1 for u in users if (u.get("created_at") or "")[:10] >= week.isoformat()[:10])
        views_7d = sum(1 for t in traffic if (t.get("created_at") or "")[:10] >= week.isoformat()[:10])
        plan_counts = {}
        for u in users:
            plan_counts[u.get("plan", "free")] = plan_counts.get(u.get("plan", "free"), 0) + 1
        ai_calls = sum(1 for l in logs if l.get("action_type") == "ai_reply_sent")
        return {
            "users_total": len(users),
            "users_active": sum(1 for u in users if u.get("is_active")),
            "signups_7d": signups_7d,
            "traffic_views_7d": views_7d,
            "leads_total": len(leads),
            "operations_total": len(logs),
            "ai_calls": ai_calls,
            "plan_distribution": plan_counts,
        }

    @app.get("/api/admin/traffic", tags=["Admin Console"])
    async def recent_traffic(request: Request, limit: int = 100):
        _require_admin(request)
        rows = supabase_db.select("site_traffic") or []
        rows.sort(key=lambda r: r.get("created_at") or "", reverse=True)
        # aggregate per path
        by_path = {}
        for r in rows:
            by_path[r.get("path", "?")] = by_path.get(r.get("path", "?"), 0) + 1
        return {"status": "success", "total": len(rows),
                "recent": rows[:min(max(limit, 1), 300)],
                "by_path": dict(sorted(by_path.items(), key=lambda kv: -kv[1])[:20])}

    @app.get("/api/admin/system/health", tags=["Admin Console"])
    async def system_health(request: Request):
        _require_admin(request)
        import time
        from src.config import settings
        t0 = time.time()
        db_connected = False
        db_latency_ms = None
        try:
            supabase_db.select("app_settings")
            db_connected = True
            db_latency_ms = round((time.time() - t0) * 1000, 1)
        except Exception as e:
            logger.warning(f"Health check DB ping failed: {e}")
            db_connected = bool(supabase_db.is_connected)

        return {
            "status": "success",
            "database": {
                "connected": db_connected,
                "latency_ms": db_latency_ms,
                "mode": "supabase_cloud" if db_connected else "local_fallback"
            },
            "environment": {
                "meta_app_id_configured": bool(settings.META_APP_ID),
                "meta_app_secret_configured": bool(settings.META_APP_SECRET),
                "threads_app_id_configured": bool(settings.THREADS_APP_ID),
                "threads_app_secret_configured": bool(settings.THREADS_APP_SECRET),
                "gemini_api_key_configured": bool(settings.GEMINI_API_KEY),
                "polar_configured": bool(getattr(settings, "POLAR_ACCESS_TOKEN", None)),
                "cron_secret_configured": bool(getattr(settings, "CRON_SECRET", None)),
            },
            "webhook": {
                "path": "/api/webhook/meta",
                "hmac_sha256_enforced": True,
                "subscribed_fields": ["messages", "messaging_postbacks", "feed", "mention"],
                "window_policy": "24h Strict Enforcement"
            }
        }

    @app.post("/api/admin/cron/trigger/{job_name}", tags=["Admin Console"])
    async def trigger_cron_job(job_name: str, request: Request):
        _require_admin(request)
        job = job_name.lower().strip()
        from src.modules.context import (
            content_scheduler, meta_insights_sync, threads_oauth_manager
        )
        from src.modules.billing.services import entitlement_service

        try:
            if job == "scheduler":
                res = await content_scheduler.check_and_publish_due_posts()
                return {"status": "success", "job": job, "message": f"تم فحص المنشورات المجدولة (تمت معالجة {len(res)})"}
            elif job == "threads_refresh":
                res = await threads_oauth_manager.refresh_if_expiring()
                refreshed_cnt = len(res.get("refreshed", []))
                return {"status": "success", "job": job, "message": f"تم فحص توكنات ثريدز (تجديد {refreshed_cnt})"}
            elif job == "billing_reconcile":
                res = entitlement_service.reconcile_active_subscriptions()
                return {"status": "success", "job": job, "message": f"تمت مطابقة اشتراكات Polar بنجاح ({len(res.get('outcomes', []))} حساب)"}
            elif job == "insights":
                rows = supabase_db.select("platform_connections", {"status": "active"}) or []
                owner_ids = sorted({str(r.get("user_id")) for r in rows if r.get("user_id")})
                for oid in owner_ids:
                    await meta_insights_sync.sync_recent_metrics(oid, days=7)
                return {"status": "success", "job": job, "message": f"تمت مزامنة إحصائيات ميتا لـ {len(owner_ids)} حساب"}
            else:
                raise HTTPException(status_code=400, detail=f"مهمة غير معروفة: {job_name}")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Admin trigger cron failed for {job}: {e}")
            return {"status": "error", "job": job, "detail": str(e)[:200]}


module_registry.register_module(
    name="admin_console",
    description="Owner Admin Console: users management (activate/edit/credits/plan), traffic log, KPIs",
    register_router=register,
)

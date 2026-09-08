"""
Admin System Alerts (Phase 7 of Roadmap v2).

Monitors everything that can expire or silently break and surfaces colored
banners in the admin dashboard:
- Meta Page token validity (invalidated by password change!)
- Threads token expiry (warns < 14 days, offers refresh)
- Gemini API reachability + quota errors
- Webhook subscription status
- Scheduler last-run freshness (cron-job.org)
- Supabase connectivity
"""
import time
from typing import Any, Dict, List

import httpx

from src.config import settings
from src.core.logger import logger
from src.core.supabase_client import supabase_db

from src.meta_api.threads_oauth import get_active_threads_token

CACHE_TTL = 120  # seconds — avoid hammering external APIs on every dashboard poll
TOKEN_WARN_DAYS = 14

_alerts_cache: Dict[str, Any] = {"ts": 0.0, "alerts": None}


def _check_meta_token() -> Dict[str, Any]:
    """Validates the Page token via debug_token."""
    token = settings.META_PAGE_ACCESS_TOKEN
    if not token or token.startswith("your-"):
        return {"id": "meta_token", "level": "warning",
                "title_ar": "توكن فيسبوك غير مضبوط", "title_en": "Meta token not configured"}
    try:
        r = httpx.get(
            f"{settings.META_GRAPH_API_BASE_URL}/debug_token",
            params={"input_token": token,
                    "access_token": f"{settings.META_APP_ID}|{settings.META_APP_SECRET}"},
            timeout=10,
        )
        d = r.json().get("data", {})
        if not d.get("is_valid"):
            return {"id": "meta_token", "level": "critical",
                    "title_ar": "🔴 توكن فيسبوك مُبطل — الردود الآلية متوقفة! (سبب شائع: تغيير كلمة مرور فيسبوك)",
                    "title_en": "🔴 Meta token INVALID — automation stopped! (common cause: password change)"}
        return {"id": "meta_token", "level": "ok", "title_ar": "توكن فيسبوك سليم", "title_en": "Meta token valid"}
    except Exception as e:
        return {"id": "meta_token", "level": "warning",
                "title_ar": f"تعذر فحص توكن فيسبوك: {str(e)[:80]}", "title_en": f"Meta token check failed: {str(e)[:80]}"}


def _check_threads_token() -> Dict[str, Any]:
    """Checks Threads token existence + expiry window."""
    creds = {}
    try:
        creds = supabase_db.get_setting("threads_credentials") or {}
    except Exception:
        pass
    token = creds.get("access_token")
    if not token:
        return {"id": "threads_token", "level": "info",
                "title_ar": "حساب Threads غير مربوط بعد — اربطه من الإعدادات",
                "title_en": "Threads not connected yet — connect from Settings"}
    expires_at = creds.get("expires_at", 0)
    days_left = (expires_at - time.time()) / 86400
    if days_left <= 0:
        return {"id": "threads_token", "level": "critical",
                "title_ar": "🔴 توكن Threads انتهى — أعد الربط من الإعدادات",
                "title_en": "🔴 Threads token EXPIRED — reconnect from Settings"}
    if days_left < TOKEN_WARN_DAYS:
        return {"id": "threads_token", "level": "warning",
                "title_ar": f"⚠️ توكن Threads ينتهي بعد {int(days_left)} يوم — اضغط Refresh Token",
                "title_en": f"⚠️ Threads token expires in {int(days_left)} days — press Refresh Token"}
    return {"id": "threads_token", "level": "ok",
            "title_ar": f"Threads مربوط (@{creds.get('threads_username', '')}) — {int(days_left)} يوم متبقي",
            "title_en": f"Threads connected (@{creds.get('threads_username', '')}) — {int(days_left)} days left"}


def _check_gemini() -> Dict[str, Any]:
    """Tiny live Gemini call to detect quota/auth issues.
    Honest 429 handling: free tier = ~20 requests/MINUTE for flash models —
    health-check calls themselves can trip it. Reports per-minute vs daily
    based on Google's retry hint instead of always claiming 'daily quota'."""
    key = settings.GEMINI_API_KEY
    if not key or key.startswith("your-"):
        return {"id": "gemini", "level": "warning",
                "title_ar": "مفتاح Gemini غير مضبوط — الردود تعمل بالقوالب الاحتياطية",
                "title_en": "Gemini key missing — replies use fallback templates"}
    try:
        r = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{settings.LLM_MODEL}:generateContent",
            headers={"Content-Type": "application/json", "X-goog-api-key": key},
            json={"contents": [{"parts": [{"text": "OK"}]}],
                  "generationConfig": {"maxOutputTokens": 5, "thinkingConfig": {"thinkingBudget": 0}}},
            timeout=15,
        )
        if r.status_code == 200:
            return {"id": "gemini", "level": "ok", "title_ar": "Gemini يعمل", "title_en": "Gemini operational"}
        if r.status_code == 429:
            # Parse Google's error body: 'retry in Xs' — small X = per-minute limit
            body = ""
            try:
                body = r.json().get("error", {}).get("message", "")
            except Exception:
                body = r.text[:500]
            retry_seconds = None
            import re as _re
            m = _re.search(r"retry in ([\d.]+)s", body, _re.IGNORECASE)
            if m:
                retry_seconds = float(m.group(1))
            if retry_seconds is not None and retry_seconds < 120:
                return {"id": "gemini", "level": "warning",
                        "title_ar": f"⚠️ Gemini: تجاوزنا حد الدقيقة المجاني (20 طلب/دقيقة) — يستأنف بعد {int(retry_seconds)} ثانية. الوكيل شغال طبيعي — ده سببه فحوصات الصحة المتكررة",
                        "title_en": f"⚠️ Gemini per-minute free limit hit (20 req/min) — resumes in {int(retry_seconds)}s. Agent is fine — caused by frequent health checks"}
            return {"id": "gemini", "level": "warning",
                    "title_ar": "⚠️ حصة Gemini اليومية استُنفدت — القوالب الاحتياطية تعمل مؤقتاً",
                    "title_en": "⚠️ Gemini daily quota exhausted — fallback templates active"}
        return {"id": "gemini", "level": "warning",
                "title_ar": f"⚠️ Gemini يستجيب بخطأ {r.status_code}", "title_en": f"⚠️ Gemini error {r.status_code}"}
    except Exception as e:
        return {"id": "gemini", "level": "warning",
                "title_ar": f"⚠️ Gemini غير قابل للوصول: {str(e)[:60]}", "title_en": f"⚠️ Gemini unreachable: {str(e)[:60]}"}


def _check_webhook_subscription() -> Dict[str, Any]:
    """Verifies the page is still subscribed to app webhooks."""
    token = settings.META_PAGE_ACCESS_TOKEN
    page_id = settings.META_PAGE_ID
    if not token or not page_id or token.startswith("your-"):
        return {"id": "webhook", "level": "info", "title_ar": "الويب هوك: توكن غير متوفر", "title_en": "Webhook: token unavailable"}
    try:
        r = httpx.get(
            f"{settings.META_GRAPH_API_BASE_URL}/{page_id}/subscribed_apps",
            params={"access_token": token}, timeout=10,
        )
        if r.status_code == 200:
            apps = r.json().get("data", [])
            app_ids = [a.get("id") for a in apps]
            if settings.META_APP_ID in app_ids:
                return {"id": "webhook", "level": "ok", "title_ar": "الويب هوك مشترك وفعال", "title_en": "Webhook subscribed"}
            return {"id": "webhook", "level": "critical",
                    "title_ar": "🔴 الصفحة غير مشتركة بالويب هوك — الرسائل لن تصل! اضغط Subscribe من الإعدادات",
                    "title_en": "🔴 Page not subscribed to webhooks — messages won't arrive! Press Subscribe in Settings"}
        return {"id": "webhook", "level": "warning",
                "title_ar": f"فحص الويب هوك فشل ({r.status_code})", "title_en": f"Webhook check failed ({r.status_code})"}
    except Exception as e:
        return {"id": "webhook", "level": "warning",
                "title_ar": f"خطأ فحص الويب هوك: {str(e)[:60]}", "title_en": f"Webhook check error: {str(e)[:60]}"}


def _check_scheduler() -> Dict[str, Any]:
    """Checks recent activity_logs for cron-driven scheduler runs."""
    try:
        rows = supabase_db.select("activity_logs") or []
        # Any log row written in the last 25 hours proves the app is alive & cron reachable
        recent = [r_ for r_ in rows if (r_.get("executed_at") or "") >= time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(time.time() - 25 * 3600))]
        if recent:
            return {"id": "scheduler", "level": "ok", "title_ar": "السكيدولر يعمل (cron نشط)", "title_en": "Scheduler active (cron live)"}
        return {"id": "scheduler", "level": "warning",
                "title_ar": "⚠️ لا حركة مسجلة منذ 25 ساعة — افحص cron-job.org",
                "title_en": "⚠️ No logged activity in 25h — check cron-job.org"}
    except Exception:
        return {"id": "scheduler", "level": "info", "title_ar": "فحص السكيدولر: تخطي", "title_en": "Scheduler check: skipped"}


def _check_supabase() -> Dict[str, Any]:
    if supabase_db.is_connected:
        return {"id": "supabase", "level": "ok", "title_ar": "قاعدة البيانات متصلة", "title_en": "Database connected"}
    return {"id": "supabase", "level": "critical",
            "title_ar": "🔴 قاعدة البيانات غير متصلة — وضع الذاكرة المؤقتة!",
            "title_en": "🔴 Database disconnected — running on in-memory store!"}


def collect_alerts(force: bool = False) -> List[Dict[str, Any]]:
    """Runs all checks. Two-layer cache to stop burning external quotas:
    1) In-memory per-instance (fast, 120s TTL)
    2) Shared Supabase app_settings cache ('system_alerts_cache') so all
       serverless instances reuse one round of checks (10-min TTL) —
       previously every cold start re-hit Meta+Gemini and the Gemini
       free tier (20 req/min) got exhausted by HEALTH CHECKS alone."""
    now = time.time()
    if not force and _alerts_cache["alerts"] is not None and (now - _alerts_cache["ts"]) < CACHE_TTL:
        return _alerts_cache["alerts"]

    # Shared cache read (skip when force=True — admin clicked re-run)
    if not force:
        try:
            shared = supabase_db.get_setting("system_alerts_cache") or {}
            if isinstance(shared, dict) and shared.get("alerts") and (now - float(shared.get("ts", 0))) < 600:
                _alerts_cache["ts"] = now
                _alerts_cache["alerts"] = shared["alerts"]
                return shared["alerts"]
        except Exception:
            pass

    checks = [
        _check_meta_token(),
        _check_threads_token(),
        _check_gemini(),
        _check_webhook_subscription(),
        _check_scheduler(),
        _check_supabase(),
    ]
    order = {"critical": 0, "warning": 1, "info": 2, "ok": 3}
    checks.sort(key=lambda a: order.get(a["level"], 9))
    _alerts_cache["ts"] = now
    _alerts_cache["alerts"] = checks

    # Persist to shared cache (best-effort)
    try:
        supabase_db.set_setting("system_alerts_cache", {"ts": now, "alerts": checks})
    except Exception:
        pass
    return checks

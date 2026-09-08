"""
Data Privacy endpoints required for Meta App Review & platform compliance:
- /privacy           : Public privacy policy page
- /data-deletion     : Data deletion instructions page + deletion callback API

Registered explicitly via register_compliance_routes(app) to avoid circular imports.
"""
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from src.core.supabase_client import supabase_db
from src.core.logger import logger


# Kept for backward compatibility with the JSON admin format
class DataDeletionCallback(BaseModel):
    user_id: Optional[str] = None
    email: Optional[str] = None


_PRIVACY_HTML = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>هدهد · سياسة الخصوصية</title>
<style>
body{font-family:'Tajawal',system-ui,sans-serif;background:#f8fafc;color:#0f172a;line-height:1.8;margin:0;padding:40px 20px;}
.wrap{max-width:760px;margin:0 auto;background:#fff;border:1px solid #e2e8f0;border-radius:16px;padding:40px;}
h1{font-size:26px;margin:0 0 8px;} h2{font-size:18px;margin-top:28px;border-bottom:1px solid #e2e8f0;padding-bottom:8px;}
.meta{color:#64748b;font-size:13px;margin-bottom:24px;} a{color:#2563eb;}
</style>
</head>
<body><div class="wrap">
<h1>سياسة الخصوصية — هدهد (Hudhud)</h1>
<div class="meta">آخر تحديث: 2026-09-06</div>

<h2>1. البيانات التي نجمعها</h2>
<p>يقوم نظام هدهد بجمع ومعالجة البيانات التالية عند ربط صفحاتك:</p>
<ul>
<li>بيانات حساباتك التجارية على فيسبوك وإنستغرام (اسم الصفحة، المعرّفات، توكن الوصول).</li>
<li>رسائل العملاء الواردة إليك وتعليقاتهم على منشوراتك، لأتمتة الردود وإدارة العملاء.</li>
<li>بيانات العملاء المتاحة علناً (الاسم، اسم المستخدم، بيانات التواصل التي يشاركها العميل بنفسه).</li>
<li>بيانات حسابك في منصتنا (البريد، رقم الهاتف، الاسم).</li>
</ul>

<h2>2. كيف نستخدم البيانات</h2>
<ul>
<li>الرد التلقائي على استفسارات العملاء عبر قنوات ميتا الرسمية (Graph API) فقط.</li>
<li>تقديم تقارير وتحليلات لأداء صفحاتك.</li>
<li>لا نبيع أو نشارك بياناتك أو بيانات عملائك مع أي طرف ثالث إطلاقاً.</li>
</ul>

<h2>3. حفظ البيانات وأمانها</h2>
<p>تُخزن البيانات في قاعدة بيانات PostgreSQL مستضافة على Supabase مع تفعيل سياسات أمان الصفوف (RLS). كلمات المرور مُشفّرة بـ PBKDF2، والجلسات موقّعة رقمياً.</p>

<h2>4. حذف البيانات</h2>
<p>يمكنك حذف حسابك وكل بياناتك المرتبطة في أي وقت عبر صفحة <a href="/data-deletion">حذف البيانات</a>.</p>

<h2>5. التواصل</h2>
<p>لأي استفسار حول الخصوصية: استخدم صفحة التواصل في المنصة.</p>
</div></body></html>"""


_DELETION_HTML = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>هدهد · حذف البيانات</title>
<style>
body{font-family:'Tajawal',system-ui,sans-serif;background:#f8fafc;color:#0f172a;line-height:1.8;margin:0;padding:40px 20px;}
.wrap{max-width:760px;margin:0 auto;background:#fff;border:1px solid #e2e8f0;border-radius:16px;padding:40px;}
h1{font-size:26px;margin:0 0 8px;} h2{font-size:18px;margin-top:28px;border-bottom:1px solid #e2e8f0;padding-bottom:8px;}
</style>
</head>
<body><div class="wrap">
<h1>حذف بياناتك — هدهد (Hudhud)</h1>

<h2>حذف بياناتك من منصتنا</h2>
<p>لحذف حسابك وكل بيانات العملاء والرسائل المرتبطة به نهائياً، أرسل طلباً عبر حسابك في المنصة مع موضوع "حذف بيانات"، وسنتم الحذف الكامل خلال 7 أيام كحد أقصى.</p>

<h2>حذف بياناتك عبر فيسبوك/إنستغرام</h2>
<p>إذا ربطت حسابك عبر تسجيل دخول فيسبوك وتريد إزالة الصلاحيات وحذف البيانات المنقولة:</p>
<ul>
<li>افتح: إعدادات فيسبوك ← التطبيقات والمواقع ← اختر هدهد ← إزالة.</li>
<li>ثم أرسل طلب حذف لمسح نسخنا المخزنة.</li>
</ul>

<h2>ماذا يتم حذفه؟</h2>
<ul>
<li>بيانات حسابك (البريد، الهاتف، الاسم، كلمة المرور المُشفّرة).</li>
<li>توكنات الوصول لصفحاتك.</li>
<li>سجلات العملاء والمحادثات المخزنة.</li>
</ul>
</div></body></html>"""


def register_compliance_routes(app: FastAPI):
    """Registers privacy & data-deletion routes on the FastAPI app."""

    # NOTE: /privacy is now served by the dedicated legal module (bilingual,
    # full policy). This module keeps the Meta-required /data-deletion page
    # and the signed callback endpoints only.

    @app.get("/data-deletion", response_class=HTMLResponse, include_in_schema=False)
    async def data_deletion_page():
        """Data deletion instructions page (Meta App Review requirement)."""
        return HTMLResponse(content=_DELETION_HTML)

    @app.post("/api/data-deletion", tags=["Compliance"])
    async def data_deletion_callback(request: Request):
        """
        Meta Data Deletion Request Callback (REQUIRED by Meta platform terms —
        this exact endpoint URL goes in the Threads API "Delete data callback URL"
        field and App settings → Basic → Data deletion).

        Supports Meta's official form-encoded `signed_request` format AND our
        JSON admin format. Responds with the Meta-required schema:
        {"url": <status page>, "confirmation_code": <code>}
        """
        import base64
        import hashlib
        import hmac as hmac_mod
        import json as json_mod
        import secrets as secrets_mod

        from src.config import settings

        content_type = request.headers.get("content-type", "")
        user_id: Optional[str] = None
        user_email: Optional[str] = None

        # SECURITY: deletion is ONLY allowed via Meta's signed_request protocol.
        # A previous unverified application/json branch allowed anyone on the
        # internet to delete any account by email — removed (fail-closed).
        if "application/json" in content_type:
            return JSONResponse(status_code=400, content={
                "error": "data deletion requires Meta signed_request (form-encoded)"
            })
        form = await request.form()
        signed_request = form.get("signed_request")
        if not signed_request:
            return JSONResponse(status_code=400, content={"error": "signed_request required"})
        # Verify against either app secret (callback may be configured on either app)
        try:
            enc_sig, enc_payload = str(signed_request).split(".", 1)
            sig = base64.urlsafe_b64decode(enc_sig + "=" * (-len(enc_sig) % 4))
            raw = base64.urlsafe_b64decode(enc_payload + "=" * (-len(enc_payload) % 4))
            data = json_mod.loads(raw)
            verified = False
            for secret in (settings.THREADS_APP_SECRET, settings.META_APP_SECRET):
                if not secret:
                    continue
                expected = hmac_mod.new(secret.encode(), enc_payload.encode("ascii"), hashlib.sha256).digest()
                if hmac_mod.compare_digest(sig, expected):
                    verified = True
                    break
            if not verified:
                return JSONResponse(status_code=403, content={"error": "invalid signed_request signature"})
            user_id = str(data.get("user_id")) if data.get("user_id") else None
        except Exception as e:
            logger.error(f"Signed request parse failed: {e}")
            return JSONResponse(status_code=400, content={"error": "malformed signed_request"})

        if not user_id and not user_email:
            # Meta may send an app-scoped id we cannot map to a local user —
            # log it for manual action and still return a compliant confirmation.
            logger.warning("Data deletion request without mappable user id")

        deleted = {"users": 0}
        try:
            if user_id:
                try:
                    supabase_db.delete("users", user_id)
                    deleted["users"] += 1
                except Exception:
                    pass
            if user_email:
                rows = supabase_db.select("users", {"email": user_email.lower()}) or []
                for u in rows:
                    supabase_db.delete("users", u["id"])
                    deleted["users"] += 1
        except Exception as e:
            logger.error(f"Data deletion error: {e}")
            return JSONResponse(status_code=500, content={"error": "deletion failed"})

        confirmation_code = secrets_mod.token_hex(8)
        supabase_db.insert("activity_logs", {
            "action_type": "data_deletion_request",
            "platform": "system",
            "target_id": user_id or user_email or "unknown",
            "status": "success",
            "details": {"deleted": deleted, "confirmation_code": confirmation_code},
        })

        # Meta-required response schema (Data Deletion Request Callback spec)
        return JSONResponse(content={
            "url": f"{settings.APP_BASE_URL.rstrip('/')}/data-deletion?id={confirmation_code}",
            "confirmation_code": confirmation_code,
        })

    @app.post("/api/threads/uninstall", tags=["Compliance"])
    async def threads_uninstall_callback(request: Request):
        """
        Threads "Uninstall Callback URL" target. Meta POSTs a signed_request
        when a user removes the app. Verifies signature, clears stored
        Threads credentials, and logs the event. Returns 200 as required.
        """
        import base64
        import hashlib
        import hmac as hmac_mod
        import json as json_mod

        from src.config import settings

        try:
            form = await request.form()
            signed_request = form.get("signed_request")
            if not signed_request:
                return JSONResponse(status_code=400, content={"error": "signed_request required"})
            enc_sig, enc_payload = str(signed_request).split(".", 1)
            sig = base64.urlsafe_b64decode(enc_sig + "=" * (-len(enc_sig) % 4))
            raw = base64.urlsafe_b64decode(enc_payload + "=" * (-len(enc_payload) % 4))
            data = json_mod.loads(raw)
            verified = False
            for secret in (settings.THREADS_APP_SECRET, settings.META_APP_SECRET):
                if not secret:
                    continue
                expected = hmac_mod.new(secret.encode(), enc_payload.encode("ascii"), hashlib.sha256).digest()
                if hmac_mod.compare_digest(sig, expected):
                    verified = True
                    break
            if not verified:
                return JSONResponse(status_code=403, content={"error": "invalid signature"})

            # The user uninstalled → revoke stored Threads token (security)
            try:
                supabase_db.set_setting("threads_credentials", {})
            except Exception:
                pass

            supabase_db.insert("activity_logs", {
                "action_type": "threads_app_uninstalled",
                "platform": "system",
                "target_id": str(data.get("user_id", "")),
                "status": "success",
                "details": {"note": "Threads credentials cleared"},
            })
            return {}
        except Exception as e:
            logger.error(f"Uninstall callback error: {e}")
            return JSONResponse(status_code=400, content={"error": "callback failed"})

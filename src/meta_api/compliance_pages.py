"""
Data Privacy endpoints required for Meta App Review & platform compliance:
- /privacy           : Public privacy policy page
- /data-deletion     : Data deletion instructions page + deletion callback API

Registered explicitly via register_compliance_routes(app) to avoid circular imports.
"""
from typing import Optional

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from src.core.supabase_client import supabase_db
from src.core.logger import logger


class DataDeletionCallback(BaseModel):
    """Meta's signed_request style payload is parsed minimally here (dev-friendly)."""
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

    @app.get("/privacy", response_class=HTMLResponse, include_in_schema=False)
    async def privacy_policy_page():
        """Public privacy policy (Meta App Review requirement)."""
        return HTMLResponse(content=_PRIVACY_HTML)

    @app.get("/data-deletion", response_class=HTMLResponse, include_in_schema=False)
    async def data_deletion_page():
        """Data deletion instructions page (Meta App Review requirement)."""
        return HTMLResponse(content=_DELETION_HTML)

    @app.post("/api/data-deletion", tags=["Compliance"])
    async def data_deletion_callback(payload: DataDeletionCallback):
        """
        Data deletion callback. In production this receives Meta's signed_request;
        here we support explicit user_id/email deletion with audit logging.
        """
        if not payload.user_id and not payload.email:
            return JSONResponse(status_code=400, content={"detail": "user_id or email required"})

        deleted = {"users": 0}
        try:
            if payload.user_id:
                supabase_db.delete("users", payload.user_id)
                deleted["users"] = 1
            elif payload.email:
                rows = supabase_db.select("users", {"email": payload.email.lower()}) or []
                for u in rows:
                    supabase_db.delete("users", u["id"])
                    deleted["users"] += 1
        except Exception as e:
            logger.error(f"Data deletion error: {e}")
            return JSONResponse(status_code=500, content={"detail": "deletion failed"})

        supabase_db.insert("activity_logs", {
            "action_type": "data_deletion_request",
            "platform": "system",
            "target_id": payload.user_id or payload.email or "",
            "status": "success",
            "details": {"deleted": deleted},
        })
        return {
            "status": "success",
            "deleted": deleted,
            "confirmation_code": f"del-{payload.user_id or hash(payload.email or '')}",
            "message": "تم استلام طلب الحذف وتنفيذه وفق سياسة البيانات",
        }

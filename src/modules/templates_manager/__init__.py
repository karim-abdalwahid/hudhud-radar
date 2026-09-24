"""
Templates Manager module (WS-G) — editable lifecycle message templates.

Owner requirement: "قسم فيه الـ Templates المستخدمة وأقدر أعدل فيها في أي وقت".
- Templates live in message_templates (seeded 6 lifecycle events).
- Rendering: placeholder substitution {user_name} {plan} {credits}...
- Trigger → Template → Notification: lifecycle events render the template
  (if active) and deliver via notification_service (email later, v1.1).
- Admin APIs: list / get / update / restore-default / toggle.
- Page: /templates (admin-only) with bilingual live preview & editing.
"""
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from src.core.auth import verify_session_token, SESSION_COOKIE_NAME
from src.core.logger import logger
from src.core.modules import module_registry, NavEntry, PageSpec, ACCESS_ADMIN
from src.core.supabase_client import supabase_db
from src.modules.notifications.service import notification_service


# ------------------------------------------------------------------
# Built-in defaults (bilingual: English and Arabic lifecycle seeds)
# ------------------------------------------------------------------
DEFAULT_TEMPLATES: Dict[str, Dict[str, str]] = {
    "welcome_signup": {
        "subject_ar": "🎉 أهلاً بك في هدهد، {user_name}!",
        "body_ar": "حسابك جاهز الآن. الخطوة التالية: اربط صفحتك من الإعدادات وسيبدأ الوكيل الذكي بالرد على عملائك فوراً.",
        "subject_en": "🎉 Welcome to Hudhud, {user_name}!",
        "body_en": "Your account is ready. Next step: connect your social channels from Settings to activate automated replies.",
        "subject": "🎉 أهلاً بك في هدهد، {user_name}!",
        "body": "حسابك جاهز الآن. الخطوة التالية: اربط صفحتك من الإعدادات وسيبدأ الوكيل الذكي بالرد على عملائك فوراً.",
    },
    "welcome_login": {
        "subject_ar": "👋 رجوع سعيد، {user_name}",
        "body_ar": "أهلاً بعودتك! راجع إشعارات محادثاتك الجديدة من صندوق الوارد.",
        "subject_en": "👋 Welcome back, {user_name}",
        "body_en": "Welcome back! Check your latest conversations and notifications in your Live Inbox.",
        "subject": "👋 رجوع سعيد، {user_name}",
        "body": "أهلاً بعودتك! راجع إشعارات محادثاتك الجديدة من صندوق الوارد.",
    },
    "trial_ending": {
        "subject_ar": "⏳ تجربتك المجانية تنتهي قريباً",
        "body_ar": "تجربتك المجانية (3 أيام) تنتهي بتاريخ {trial_end}. للاستمرار في خدمة الردود الذكية، فعّل خطتك من لوحة التحكم.",
        "subject_en": "⏳ Your free trial is ending soon",
        "body_en": "Your 3-day free trial expires on {trial_end}. Activate your subscription to keep automated AI replies running uninterrupted.",
        "subject": "⏳ تجربتك المجانية تنتهي قريباً",
        "body": "تجربتك المجانية (3 أيام) تنتهي بتاريخ {trial_end}. للاستمرار في خدمة الردود الذكية، فعّل خطتك من لوحة التحكم.",
    },
    "plan_purchased": {
        "subject_ar": "✅ تم تفعيل خطتك: {plan}",
        "body_ar": "مبروك! خطتك ({plan}) مفعّلة الآن — رصيد الذكاء الاصطناعي المخصص أُضيف لحسابك.",
        "subject_en": "✅ Plan activated: {plan}",
        "body_en": "Congratulations! Your {plan} subscription is active — AI credits have been added to your balance.",
        "subject": "✅ تم تفعيل خطتك: {plan}",
        "body": "مبروك! خطتك ({plan}) مفعّلة الآن — رصيد الذكاء الاصطناعي المخصص أُضيف لحسابك.",
    },
    "credits_low": {
        "subject_ar": "⚠️ رصيد الذكاء الاصطناعي منخفض",
        "body_ar": "باقي لديك {credits} رصيد فقط. الوكيل سيعمل بالقوالب الاحتياطية عند النفاد — تواصل معنا للتجديد.",
        "subject_en": "⚠️ Low AI credits warning",
        "body_en": "You have {credits} credits remaining. The agent will fall back to static templates when depleted — top up anytime.",
        "subject": "⚠️ رصيد الذكاء الاصطناعي منخفض",
        "body": "باقي لديك {credits} رصيد فقط. الوكيل سيعمل بالقوالب الاحتياطية عند النفاد — تواصل معنا للتجديد.",
    },
    "agent_new_lead": {
        "subject_ar": "🎯 عميل محتمل جديد!",
        "body_ar": "الوكيل التقط عميلاً مهتماً: {lead_name} — شاهده في إدارة العملاء.",
        "subject_en": "🎯 New qualified lead captured!",
        "body_en": "Your AI agent captured a new prospect: {lead_name} — view details in your Leads CRM.",
        "subject": "🎯 عميل محتمل جديد!",
        "body": "الوكيل التقط عميلاً مهتماً: {lead_name} — شاهده في إدارة العملاء.",
    },
}

TEMPLATE_KEYS = sorted(DEFAULT_TEMPLATES.keys())


def _require_admin(request: Request) -> Dict:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    session = verify_session_token(token) if token else None
    if not session or session.get("role") != "admin":
        raise HTTPException(status_code=403, detail="هذه العملية تتطلب صلاحيات المدير")
    return session


def _fill_placeholders(text: str, values: Dict[str, Any]) -> str:
    out = text
    for k, v in (values or {}).items():
        out = out.replace("{" + k + "}", str(v))
    return out


def get_template_row(key: str) -> Optional[Dict[str, Any]]:
    rows = supabase_db.select("message_templates", {"key": key}) or []
    return rows[0] if rows else None


def render_and_notify(key: str, user_id: str, values: Optional[Dict[str, Any]] = None, lang: Optional[str] = None) -> bool:
    """Lifecycle hook: renders template `key` (if active) and notifies the user.
    Supports user language preferences ('en' vs 'ar'). Fail-silent."""
    try:
        row = get_template_row(key)
        if not row or not row.get("is_active"):
            return False  # admin disabled this template — deliver nothing
        d = DEFAULT_TEMPLATES.get(key, {})
        subj_raw = row.get("subject") or d.get("subject_ar", "")
        body_raw = row.get("body") or d.get("body_ar", "")
        if lang == "en":
            subj_raw = row.get("subject_en") or d.get("subject_en", subj_raw)
            body_raw = row.get("body_en") or d.get("body_en", body_raw)
        elif lang == "ar":
            subj_raw = row.get("subject_ar") or d.get("subject_ar", subj_raw)
            body_raw = row.get("body_ar") or d.get("body_ar", body_raw)
        subject = _fill_placeholders(subj_raw, values or {})
        body = _fill_placeholders(body_raw, values or {})
        notification_service.create(user_id, subject, body, "info",
                                    {"template": key, **(values or {})})
        return True
    except Exception as e:
        logger.warning(f"render_and_notify({key}) failed (non-blocking): {e}")
        return False


class TemplateUpdatePayload(BaseModel):
    subject: Optional[str] = None
    body: Optional[str] = None
    subject_ar: Optional[str] = None
    body_ar: Optional[str] = None
    subject_en: Optional[str] = None
    body_en: Optional[str] = None
    is_active: Optional[bool] = None


def register(app: FastAPI) -> None:
    @app.get("/api/admin/templates", tags=["Templates Manager"])
    async def list_templates(request: Request):
        _require_admin(request)
        rows = supabase_db.select("message_templates") or []
        for r in rows:
            k = r.get("key", "")
            d = DEFAULT_TEMPLATES.get(k, {})
            r.setdefault("subject_ar", d.get("subject_ar", r.get("subject", "")))
            r.setdefault("body_ar", d.get("body_ar", r.get("body", "")))
            r.setdefault("subject_en", d.get("subject_en", ""))
            r.setdefault("body_en", d.get("body_en", ""))
        rows.sort(key=lambda r: r.get("key", ""))
        return {"status": "success", "templates": rows, "known_keys": TEMPLATE_KEYS, "defaults": DEFAULT_TEMPLATES}

    @app.put("/api/admin/templates/{key}", tags=["Templates Manager"])
    async def update_template(key: str, payload: TemplateUpdatePayload, request: Request):
        _require_admin(request)
        if key not in TEMPLATE_KEYS:
            raise HTTPException(status_code=400, detail="مفتاح قالب غير معروف")
        row = get_template_row(key)
        if not row:
            raise HTTPException(status_code=404, detail="القالب غير موجود")
        updates = {k: v for k, v in payload.model_dump().items() if v is not None}
        if not updates:
            raise HTTPException(status_code=400, detail="لا يوجد شيء للتحديث")
        from datetime import datetime, timezone
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        updated = supabase_db.update("message_templates", row["id"], updates)
        return {"status": "success", "template": updated}

    @app.post("/api/admin/templates/{key}/restore", tags=["Templates Manager"])
    async def restore_template(key: str, request: Request):
        _require_admin(request)
        if key not in TEMPLATE_KEYS:
            raise HTTPException(status_code=400, detail="مفتاح قالب غير معروف")
        row = get_template_row(key)
        if not row:
            raise HTTPException(status_code=404, detail="القالب غير موجود")
        d = DEFAULT_TEMPLATES[key]
        from datetime import datetime, timezone
        updated = supabase_db.update("message_templates", row["id"], {
            "subject": d["subject"], "body": d["body"],
            "is_active": True, "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        return {"status": "success", "template": updated}

    @app.get("/templates", include_in_schema=False)
    async def templates_page(request: Request):
        session = _require_admin(request)
        html = _ADMIN_TEMPLATES_HTML
        from src.modules.pages import render_module_page
        return render_module_page(html, request)


_ADMIN_TEMPLATES_HTML = r"""<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Admin — Message Templates</title>
<link rel="icon" href="/static/favicon.ico" sizes="any">
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Tajawal:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/static/saas.css">
<style>
/* Page-only styles — shared chrome comes from saas.css (same as every page). */
.tpl-card{background:var(--bg-card);border:1px solid var(--border-default);border-radius:14px;padding:18px;margin-bottom:14px;}
.tpl-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;gap:10px;flex-wrap:wrap;}
.tpl-key{font-family:monospace;font-size:12.5px;color:var(--accent-blue);font-weight:700;}
label{display:block;font-size:11.5px;color:var(--text-muted);font-weight:700;margin:8px 0 4px;text-transform:uppercase;}
input.subject, textarea.body {width:100%;padding:9px 12px;border:1px solid var(--border-default);border-radius:9px;font-family:inherit;font-size:13px;background:var(--bg-card);color:var(--text-primary);}
textarea.body{min-height:74px;resize:vertical;line-height:1.6;}
.toggle{font-size:12px;font-weight:700;padding:4px 10px;border-radius:99px;display:inline-block;}
.on{background:#ecfdf5;color:#059669;} .off{background:#fef2f2;color:#dc2626;}
.preview{background:var(--bg-subtle);border:1px dashed var(--border-default);border-radius:9px;padding:10px 12px;font-size:12.5px;color:var(--text-secondary);margin-top:8px;white-space:pre-wrap;}
</style>
</head>
<body>
<div class="app-layout">
    <aside class="app-sidebar">
        <div class="sidebar-header">
            <a href="/dashboard" class="brand-logo-link">
                <span class="brand-logo-text">Hudhud</span><span class="brand-dot">.</span>
            </a>
            <div class="brand-sub" data-i18n="brand.tagline">Autonomous AI Social Sales Agent</div>
        </div>
        <nav class="sidebar-nav"></nav>
        <div class="sidebar-footer">
            <div id="meta-status-container" class="status-pill">
                <div id="meta-dot" class="status-dot"></div>
                <span id="meta-status-badge" data-i18n="status.checking">Checking status...</span>
            </div>
        </div>
    </aside>
    <main class="app-main">
        <header class="app-topbar">
            <div class="topbar-breadcrumb">
                <span class="crumb-root" data-i18n="brand.name">Hudhud</span>
                <span class="crumb-sep">/</span>
                <span class="crumb-current" data-i18n="tpl.title">Message Templates</span>
            </div>
            <div class="topbar-actions" style="display:flex; gap:10px; align-items:center;"></div>
        </header>
        <div class="app-content">
            <div class="panel-section" style="margin-bottom:14px;">
                <div class="panel-header"><div>
                    <h3 class="panel-title" data-i18n="tpl.panel_title">Automatic Message Templates</h3>
                    <div class="panel-desc" data-i18n="tpl.panel_desc">Edit the automatic messages your platform sends (signup, trials, plans, credits, new leads). Placeholders fill automatically at send time.</div>
                </div>
                <div style="display:flex; gap:8px; align-items:center;">
                    <button type="button" class="chip active" id="btn-lang-en" onclick="setTplLang('en')" data-i18n="tpl.lang_en">English View</button>
                    <button type="button" class="chip" id="btn-lang-ar" onclick="setTplLang('ar')" data-i18n="tpl.lang_ar">العرض بالعربية</button>
                </div></div>
            </div>
            <div id="tpl-list"><div style="color:var(--text-muted);">Loading…</div></div>
        </div>
    </main>
</div>
<script src="/static/i18n.js"></script>
<script src="/static/saas.js"></script>
<script>
const PLACEHOLDERS = {
    welcome_signup: '{user_name}',
    welcome_login: '{user_name}',
    trial_ending: '{trial_end}',
    plan_purchased: '{plan}',
    credits_low: '{credits}',
    agent_new_lead: '{lead_name}'
};
let tplLang = 'en';
let allTemplates = [];
let allDefaults = {};

function setTplLang(lang) {
    tplLang = lang;
    const bEn = document.getElementById('btn-lang-en');
    const bAr = document.getElementById('btn-lang-ar');
    if (bEn) bEn.className = 'chip' + (lang === 'en' ? ' active' : '');
    if (bAr) bAr.className = 'chip' + (lang === 'ar' ? ' active' : '');
    renderTemplates();
}

async function load() {
    tplLang = (window.hudhudI18n && window.hudhudI18n.currentLang) || 'en';
    const bEn = document.getElementById('btn-lang-en');
    const bAr = document.getElementById('btn-lang-ar');
    if (bEn) bEn.className = 'chip' + (tplLang === 'en' ? ' active' : '');
    if (bAr) bAr.className = 'chip' + (tplLang === 'ar' ? ' active' : '');

    const r = await fetch('/api/admin/templates');
    const d = await r.json();
    allTemplates = d.templates || [];
    allDefaults = d.defaults || {};
    renderTemplates();
}

function renderTemplates() {
    const box = document.getElementById('tpl-list');
    box.innerHTML = allTemplates.map(t => {
        const def = allDefaults[t.key] || {};
        const isEn = tplLang === 'en';
        const subj = isEn ? (t.subject_en || def.subject_en || t.subject) : (t.subject_ar || def.subject_ar || t.subject);
        const body = isEn ? (t.body_en || def.body_en || t.body) : (t.body_ar || def.body_ar || t.body);
        const dir = isEn ? 'ltr' : 'rtl';
        return `
        <div class="tpl-card" data-key="${t.key}">
            <div class="tpl-head">
                <span class="tpl-key">${t.key}</span>
                <span>
                    <span class="toggle ${t.is_active ? 'on' : 'off'}">${t.is_active ? 'ACTIVE' : 'DISABLED'}</span>
                    <button class="btn btn-ghost" onclick="toggleActive('${t.key}', ${t.is_active})">${t.is_active ? 'Disable' : 'Enable'}</button>
                    <button class="btn btn-warn" onclick="restoreDefault('${t.key}')">↺ Restore default</button>
                </span>
            </div>
            <label>Subject (${isEn ? 'English' : 'العربية'})</label>
            <input class="subject" id="subj-${t.key}" value="${escapeHtml(subj)}" style="direction:${dir};">
            <label>Body (${isEn ? 'English' : 'العربية'}) — placeholders: <code>${PLACEHOLDERS[t.key] || '{user_name}'}</code></label>
            <textarea class="body" id="body-${t.key}" style="direction:${dir};">${escapeHtml(body)}</textarea>
            <div style="margin-top:8px;">
                <button class="btn btn-primary" onclick="saveTemplate('${t.key}')">💾 Save</button>
                <button class="btn btn-ghost" onclick="previewTemplate('${t.key}')">👁 Preview</button>
            </div>
            <div class="preview" id="prev-${t.key}" style="display:none; direction:${dir};"></div>
        </div>`;
    }).join('');
}

async function saveTemplate(key) {
    const subject = document.getElementById('subj-' + key).value;
    const body = document.getElementById('body-' + key).value;
    const isEn = tplLang === 'en';
    const payload = isEn
        ? { subject_en: subject, body_en: body, subject: subject, body: body }
        : { subject_ar: subject, body_ar: body, subject: subject, body: body };
    const r = await fetch(`/api/admin/templates/${key}`, {
        method: 'PUT', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
    });
    if (r.ok) {
        if (window.hudhudToast) hudhudToast.success('Template saved successfully');
        await load();
    } else {
        const d = await r.json();
        if (window.hudhudToast) hudhudToast.error(d.detail || 'Save failed');
        else alert(d.detail || 'Save failed');
    }
}

async function toggleActive(key, current) {
    await fetch(`/api/admin/templates/${key}`, {
        method: 'PUT', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ is_active: !current })
    });
    await load();
}

async function restoreDefault(key) {
    if (!confirm('Restore default template?')) return;
    const def = allDefaults[key] || {};
    const isEn = tplLang === 'en';
    const subj = isEn ? def.subject_en : def.subject_ar;
    const body = isEn ? def.body_en : def.body_ar;
    const payload = { subject: subj, body: body, is_active: true };
    await fetch(`/api/admin/templates/${key}`, {
        method: 'PUT', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
    });
    await load();
}

function previewTemplate(key) {
    const box = document.getElementById('prev-' + key);
    const subject = document.getElementById('subj-' + key).value;
    const body = document.getElementById('body-' + key).value;
    const isEn = tplLang === 'en';
    const ph = PLACEHOLDERS[key] || '{user_name}';
    const sample = ph.replace(/\{(\w+)\}/g, (m, k) => ({
        user_name: isEn ? 'John Smith' : 'أحمد محمد',
        trial_end: '2026-09-30',
        plan: 'Growth Pro',
        credits: '12',
        lead_name: isEn ? 'Sarah Miller' : 'سارة م.'
    }[k] || m));
    box.style.display = 'block';
    box.textContent = `📌 ${subject.replace(ph, sample)}\n\n${body.replace(ph, sample)}`;
}

document.addEventListener('DOMContentLoaded', load);
</script>
</body>
</html>"""


module_registry.register_module(
    name="templates_manager",
    description="Editable lifecycle message templates: admin page /templates, render-to-notification hooks",
    register_router=register,
    pages=[PageSpec(path="/templates", template="admin_templates", access=ACCESS_ADMIN)],
    nav=[NavEntry(href="/templates", label_key="nav.templates_admin", icon="📝",
                  section="nav.analytics_system", order=4, admin_only=True)],
)

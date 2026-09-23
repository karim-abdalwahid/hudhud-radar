"""
Account module — the customer-facing account page (/account).

Why this module exists
----------------------
Everything a paying (non-admin) customer needs to operate their OWN account
used to live inside /settings, which is an ADMIN-ONLY page (Meta Graph
diagnostics, never-expiring token generator, AI provider registry, webhook
subscriptions).  The result was that a customer could not:

  * pause their own AI agent          (API existed: /api/ai/pause)
  * change their own password         (API existed: /auth/change-password)
  * disconnect a connected channel    (API existed: DELETE /api/connections/{p})
  * connect / disconnect Threads      (API existed: /api/threads/*)
  * see their own subscription state  (API existed: /api/billing/subscription)

Every one of those APIs is already tenant-scoped to the session user, so this
module adds NO new privileges — it only exposes what the customer already owns
through a page they are allowed to open.  /settings stays admin-only and keeps
the platform-operator tooling.

Access: ACCESS_USER.  The page renders for any authenticated session; every
action it performs is scoped server-side by the session cookie.
"""
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

from src.core.auth import verify_session_token, SESSION_COOKIE_NAME
from src.core.modules import module_registry, NavEntry, PageSpec, ACCESS_USER


def register(app: FastAPI) -> None:
    @app.get("/account", include_in_schema=False)
    async def account_page(request: Request):
        # The global auth middleware already rejects sessionless requests for
        # non-public paths; reading the session here is only for the greeting.
        session = verify_session_token(request.cookies.get(SESSION_COOKIE_NAME) or "")
        email = (session or {}).get("email", "")
        html = _ACCOUNT_HTML.replace("__ACCOUNT_EMAIL__", email)
        from src.modules.pages import render_module_page
        return render_module_page(html, request)


_ACCOUNT_HTML = r"""<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Hudhud — My Account</title>
<link rel="icon" href="/static/favicon.ico" sizes="any">
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Tajawal:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/static/saas.css">
<style>
/* Page-only styles — shared chrome comes from saas.css (same as every page). */
.acct-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:14px;}
.acct-card{background:var(--bg-card);border:1px solid var(--border-default);border-radius:14px;padding:18px;}
.acct-card h3{font-size:15px;font-weight:700;margin:0 0 4px;display:flex;align-items:center;gap:8px;}
.acct-desc{font-size:12.5px;color:var(--text-muted);line-height:1.6;margin-bottom:14px;}
.acct-row{display:flex;align-items:center;justify-content:space-between;gap:12px;
          padding:11px 0;border-bottom:1px solid var(--border-default);flex-wrap:wrap;}
.acct-row:last-child{border-bottom:none;}
.acct-name{font-size:13.5px;font-weight:600;}
.acct-sub{font-size:11.5px;color:var(--text-muted);margin-top:2px;}
.pill{font-size:11.5px;font-weight:700;padding:4px 11px;border-radius:99px;display:inline-block;}
.pill-on{background:#ecfdf5;color:#059669;} .pill-off{background:#fef2f2;color:#dc2626;}
.pill-warn{background:#fffbeb;color:#b45309;} .pill-mut{background:var(--bg-subtle);color:var(--text-muted);}
.btn-sm{padding:7px 14px;font-size:12.5px;font-weight:700;border-radius:8px;cursor:pointer;
        border:1px solid var(--border-default);background:var(--bg-card);color:var(--text-primary);}
.btn-sm:hover{border-color:var(--text-muted);}
.btn-danger{border-color:#dc2626;color:#dc2626;}
.btn-danger:hover{background:#fef2f2;}
.btn-sm:disabled{opacity:.5;cursor:not-allowed;}
.acct-field{margin-bottom:11px;}
.acct-field label{display:block;font-size:12px;font-weight:600;color:var(--text-secondary);margin-bottom:4px;}
.acct-field input{width:100%;padding:10px 12px;border-radius:10px;border:1px solid var(--border-default);
                  background:var(--bg-subtle);color:var(--text-primary);font-family:inherit;font-size:13px;}
.acct-status{font-size:12.5px;min-height:18px;margin-top:8px;}
.acct-empty{font-size:12.5px;color:var(--text-muted);padding:14px 0;text-align:center;}
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
                <span class="crumb-current" id="crumb-account">My Account</span>
            </div>
            <div class="topbar-actions" style="display:flex; gap:10px; align-items:center;">
                <button type="button" class="lang-switcher-btn" onclick="window.hudhudI18n.toggle()">
                    <span data-i18n="lang.switch_btn">🌐 العربية</span>
                </button>
            </div>
        </header>
        <div class="app-content">
            <div id="acct-banner"></div>
            <div class="acct-grid">

                <!-- Subscription ------------------------------------------->
                <div class="acct-card" id="card-sub">
                    <h3>💳 <span id="h-sub"></span></h3>
                    <div class="acct-desc" id="d-sub"></div>
                    <div id="sub-body" class="acct-empty">…</div>
                </div>

                <!-- AI master switch ---------------------------------------->
                <div class="acct-card">
                    <h3>🤖 <span id="h-ai"></span></h3>
                    <div class="acct-desc" id="d-ai"></div>
                    <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
                        <span class="pill pill-mut" id="ai-badge">…</span>
                        <button type="button" class="btn-sm" id="btn-ai" onclick="toggleAi()">…</button>
                    </div>
                    <div class="acct-status" id="ai-status"></div>
                </div>

                <!-- Connected channels -------------------------------------->
                <div class="acct-card" style="grid-column:1/-1;">
                    <h3>🔗 <span id="h-conn"></span></h3>
                    <div class="acct-desc" id="d-conn"></div>
                    <div id="conn-body" class="acct-empty">…</div>
                    <div class="acct-status" id="conn-status"></div>
                </div>

                <!-- Password ------------------------------------------------>
                <div class="acct-card">
                    <h3>🔐 <span id="h-pw"></span></h3>
                    <div class="acct-desc" id="d-pw"></div>
                    <div style="max-width:420px;">
                        <div class="acct-field">
                            <label id="l-pw-cur"></label>
                            <input type="password" id="pw-current" autocomplete="current-password">
                        </div>
                        <div class="acct-field">
                            <label id="l-pw-new"></label>
                            <input type="password" id="pw-new" autocomplete="new-password">
                        </div>
                        <div class="acct-field">
                            <label id="l-pw-cf"></label>
                            <input type="password" id="pw-confirm" autocomplete="new-password">
                        </div>
                        <button type="button" class="btn-sm" id="btn-pw" onclick="changePassword()">…</button>
                        <div class="acct-status" id="pw-status"></div>
                    </div>
                </div>

                <!-- Identity ------------------------------------------------>
                <div class="acct-card">
                    <h3>👤 <span id="h-id"></span></h3>
                    <div class="acct-desc" id="d-id"></div>
                    <div class="acct-row">
                        <div><div class="acct-name" id="acct-email">__ACCOUNT_EMAIL__</div>
                             <div class="acct-sub" id="s-email"></div></div>
                    </div>
                    <div class="acct-row">
                        <div><div class="acct-name" id="l-signout"></div>
                             <div class="acct-sub" id="s-signout"></div></div>
                        <button type="button" class="btn-sm" onclick="signOut()" id="btn-signout">…</button>
                    </div>
                </div>

            </div>
        </div>
    </main>
</div>
<script src="/static/i18n.js"></script>
<script src="/static/saas.js"></script>
<script>
// Bilingual labels live here rather than in i18n.js so this page adds no
// missing-key risk: hudhudI18n.t() returns the raw key when one is absent,
// which would print "acct.title" on screen.
function isAr() { return !!(window.hudhudI18n && window.hudhudI18n.currentLang === 'ar'); }
function L(ar, en) { return isAr() ? ar : en; }
function setText(id, ar, en) { const el = document.getElementById(id); if (el) el.textContent = L(ar, en); }
function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g,
        c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

const PLATFORM_LABEL = {
    facebook:  { ar: 'فيسبوك',    en: 'Facebook',  icon: '📘' },
    instagram: { ar: 'إنستجرام',  en: 'Instagram', icon: '📸' },
    threads:   { ar: 'ثريدز',     en: 'Threads',   icon: '🧵' }
};

function paintStaticLabels() {
    document.title = L('هدهد — حسابي', 'Hudhud — My Account');
    setText('crumb-account', 'حسابي', 'My Account');
    setText('h-sub', 'الاشتراك والخطة', 'Subscription & plan');
    setText('d-sub', 'حالة اشتراكك والمنصات المتاحة في خطتك الحالية.',
                     'Your subscription status and the platforms included in your current plan.');
    setText('h-ai', 'مفتاح الردود الآلية', 'AI master switch');
    setText('d-ai', 'أوقف الذكاء الاصطناعي عبر كل محادثاتك وتعليقاتك لتدير حساباتك بنفسك. الرسائل الجديدة تظل تظهر في صندوق الوارد للرد اليدوي، وإيقاف المحادثة الواحدة (Human Takeover) يعمل بشكل مستقل.',
                    'Pause the AI across all your conversations and comment automations to manage your accounts yourself. New messages still arrive in your inbox for manual replies, and per-conversation Human Takeover stays independent.');
    setText('h-conn', 'الحسابات المربوطة', 'Connected channels');
    setText('d-conn', 'القنوات المتصلة بحسابك. فصل أي قناة يوقف ردود الوكيل عليها فوراً ولا يحذف بياناتك أو محادثاتك السابقة.',
                      'Channels linked to your account. Disconnecting one stops the agent replying there immediately; it does not delete your data or past conversations.');
    setText('h-pw', 'تغيير كلمة المرور', 'Change password');
    setText('d-pw', 'التغيير فوري ويتطلب كلمة المرور الحالية.',
                    'The change is instant and requires your current password.');
    setText('l-pw-cur', 'كلمة المرور الحالية', 'Current password');
    setText('l-pw-new', 'كلمة المرور الجديدة (8 أحرف على الأقل)', 'New password (8+ characters)');
    setText('l-pw-cf', 'تأكيد كلمة المرور الجديدة', 'Confirm new password');
    setText('btn-pw', '💾 حفظ كلمة المرور', '💾 Save password');
    setText('h-id', 'بيانات الحساب', 'Account details');
    setText('d-id', 'الحساب المستخدم لتسجيل الدخول لهذه المنصة.',
                    'The account you use to sign in to this platform.');
    setText('s-email', 'البريد الإلكتروني', 'Email address');
    setText('l-signout', 'تسجيل الخروج', 'Sign out');
    setText('s-signout', 'إنهاء الجلسة على هذا الجهاز', 'End the session on this device');
    setText('btn-signout', 'خروج', 'Sign out');
}

// ---- connect-result banner (OAuth callbacks land back here) --------------
function paintBanner() {
    const q = new URLSearchParams(location.search);
    const ok = q.get('connected');
    const err = q.get('connect_error');
    const th = q.get('threads');
    const box = document.getElementById('acct-banner');
    if (!box) return;
    let html = '';
    const name = p => (PLATFORM_LABEL[p] ? L(PLATFORM_LABEL[p].ar, PLATFORM_LABEL[p].en) : esc(p || ''));
    if (ok || th === 'connected') {
        const p = ok || 'threads';
        html = `<div class="acct-card" style="border-color:#059669;margin-bottom:14px;">
                    <div style="color:#059669;font-weight:700;font-size:13.5px;">✅ ${
                        L('تم ربط ' + name(p) + ' بنجاح.', name(p) + ' connected successfully.')}</div>
                </div>`;
    } else if (err || th === 'error') {
        const reasons = {
            invalid_state: L('انتهت صلاحية طلب الربط. حاول مرة أخرى.', 'The connect request expired. Please try again.'),
            no_pages:      L('لا توجد صفحات مُدارة على هذا الحساب.', 'No managed Pages were found on that account.'),
            store:         L('تعذر حفظ الاتصال. حاول مرة أخرى.', 'We could not save the connection. Please try again.')
        };
        const msg = reasons[err] || L('فشل الربط. حاول مرة أخرى أو تواصل معنا.',
                                      'Connection failed. Please try again or contact us.');
        html = `<div class="acct-card" style="border-color:#dc2626;margin-bottom:14px;">
                    <div style="color:#dc2626;font-weight:700;font-size:13.5px;">❌ ${esc(msg)}</div>
                </div>`;
    }
    box.innerHTML = html;
    if (html) history.replaceState({}, '', '/account');
}

// ---- subscription --------------------------------------------------------
async function loadSubscription() {
    const box = document.getElementById('sub-body');
    try {
        const d = await (await fetch('/api/billing/subscription')).json();
        const status = d.status || 'none';
        const cls = (status === 'active') ? 'pill-on' : (status === 'trialing' ? 'pill-warn' : 'pill-off');
        const label = {
            active:   L('اشتراك نشط', 'Active'),
            trialing: L('تجربة مجانية', 'Free trial'),
            canceled: L('منتهي', 'Canceled'),
            none:     L('لا يوجد اشتراك', 'No subscription')
        }[status] || esc(status);
        const plats = (d.platforms || []).map(p =>
            (PLATFORM_LABEL[p] ? PLATFORM_LABEL[p].icon + ' ' + L(PLATFORM_LABEL[p].ar, PLATFORM_LABEL[p].en) : esc(p))
        ).join(' · ');
        const ends = d.trial_ends_at
            ? `<div class="acct-sub">${L('تنتهي التجربة في', 'Trial ends')}: ${esc(String(d.trial_ends_at).slice(0, 16).replace('T', ' '))}</div>`
            : '';
        box.className = '';
        box.innerHTML = `
            <div class="acct-row">
                <div><div class="acct-name">${L('الحالة', 'Status')}</div>${ends}</div>
                <span class="pill ${cls}">${label}</span>
            </div>
            <div class="acct-row">
                <div><div class="acct-name">${L('المنصات في خطتك', 'Platforms in your plan')}</div>
                     <div class="acct-sub">${plats || L('لا توجد منصات مفعّلة', 'No platforms enabled yet')}</div></div>
                <a class="btn-sm" href="/billing/checkout-page" style="text-decoration:none;">${
                    status === 'active' ? L('تعديل الخطة', 'Change plan') : L('اشترك الآن', 'Subscribe')}</a>
            </div>`;
    } catch (e) {
        box.textContent = L('تعذر تحميل بيانات الاشتراك.', 'Could not load subscription details.');
    }
}

// ---- AI master switch ----------------------------------------------------
function renderAi(d) {
    const paused = !!d.effective_paused;
    const badge = document.getElementById('ai-badge');
    const btn = document.getElementById('btn-ai');
    badge.textContent = paused ? L('⏸️ موقوف', '⏸️ Paused') : L('✅ نشط', '✅ Active');
    badge.className = 'pill ' + (paused ? 'pill-off' : 'pill-on');
    btn.textContent = paused ? L('▶️ تشغيل الردود الآلية', '▶️ Resume AI replies')
                             : L('⏸️ إيقاف الردود الآلية', '⏸️ Pause AI replies');
    btn.className = 'btn-sm' + (paused ? '' : ' btn-danger');
    const note = document.getElementById('ai-status');
    note.textContent = (d.global_paused && !d.user_paused)
        ? L('موقوف على مستوى المنصة بواسطة الإدارة.', 'Paused platform-wide by the operator.')
        : '';
    note.style.color = 'var(--text-muted)';
}

async function loadAi() {
    try { renderAi(await (await fetch('/api/ai/pause')).json()); }
    catch (e) { document.getElementById('ai-badge').textContent = L('غير متاح', 'Unavailable'); }
}

async function toggleAi() {
    const btn = document.getElementById('btn-ai');
    btn.disabled = true;
    try {
        const cur = await (await fetch('/api/ai/pause')).json();
        const r = await fetch('/api/ai/pause', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ paused: !cur.effective_paused })
        });
        const d = await r.json();
        if (r.ok) renderAi(d); else throw new Error(d.detail || 'failed');
    } catch (e) {
        const s = document.getElementById('ai-status');
        s.textContent = L('تعذر تغيير الحالة.', 'Could not change the state.');
        s.style.color = '#dc2626';
    } finally { btn.disabled = false; }
}

// ---- connected channels --------------------------------------------------
async function loadConnections() {
    const box = document.getElementById('conn-body');
    let data = {};
    try { data = await (await fetch('/api/connections')).json(); }
    catch (e) { box.textContent = L('تعذر تحميل الحسابات.', 'Could not load your channels.'); return; }

    // Threads lives in its own OAuth manager; surface it in the same list.
    let threads = null;
    try { threads = await (await fetch('/api/threads/status')).json(); } catch (e) { /* optional */ }

    const rows = [];
    for (const c of (data.connections || [])) {
        const meta = PLATFORM_LABEL[c.platform] || { ar: c.platform, en: c.platform, icon: '🔗' };
        rows.push(`
            <div class="acct-row">
                <div>
                    <div class="acct-name">${meta.icon} ${L(meta.ar, meta.en)}</div>
                    <div class="acct-sub">${esc(c.account_name || c.account_id || '')}</div>
                </div>
                <div style="display:flex;gap:8px;align-items:center;">
                    <span class="pill pill-on">${L('متصل', 'Connected')}</span>
                    <button type="button" class="btn-sm btn-danger"
                            onclick="disconnect('${esc(c.platform)}', '${esc(c.account_name || c.platform)}')">${
                        L('فصل', 'Disconnect')}</button>
                </div>
            </div>`);
    }
    if (threads && threads.connected) {
        const meta = PLATFORM_LABEL.threads;
        rows.push(`
            <div class="acct-row">
                <div>
                    <div class="acct-name">${meta.icon} ${L(meta.ar, meta.en)}</div>
                    <div class="acct-sub">${esc(threads.username ? '@' + threads.username : '')}</div>
                </div>
                <div style="display:flex;gap:8px;align-items:center;">
                    <span class="pill pill-on">${L('متصل', 'Connected')}</span>
                    <button type="button" class="btn-sm btn-danger"
                            onclick="disconnectThreads()">${L('فصل', 'Disconnect')}</button>
                </div>
            </div>`);
    }

    if (!rows.length) {
        box.className = 'acct-empty';
        box.innerHTML = `${L('لا توجد قنوات مربوطة بعد.', 'No channels connected yet.')}
            <div style="margin-top:10px;"><a class="btn-sm" href="/onboarding" style="text-decoration:none;">${
                L('اربط قناتك الأولى', 'Connect your first channel')}</a></div>`;
        return;
    }
    box.className = '';
    box.innerHTML = rows.join('') + `
        <div style="margin-top:12px;"><a class="btn-sm" href="/onboarding" style="text-decoration:none;">+ ${
            L('ربط قناة أخرى', 'Connect another channel')}</a></div>`;
}

async function disconnect(platform, label) {
    const warn = L(`سيتوقف الوكيل عن الرد على "${label}" فوراً. بياناتك ومحادثاتك السابقة تبقى كما هي. متابعة؟`,
                   `The agent will stop replying on "${label}" immediately. Your data and past conversations stay intact. Continue?`);
    if (!confirm(warn)) return;
    const s = document.getElementById('conn-status');
    try {
        const r = await fetch('/api/connections/' + encodeURIComponent(platform), { method: 'DELETE' });
        const d = await r.json();
        if (!r.ok) throw new Error(d.detail || 'failed');
        s.textContent = L('تم فصل القناة.', 'Channel disconnected.');
        s.style.color = '#059669';
    } catch (e) {
        s.textContent = L('تعذر فصل القناة. حاول مرة أخرى.', 'Could not disconnect. Please try again.');
        s.style.color = '#dc2626';
    }
    loadConnections();
}

async function disconnectThreads() {
    if (!confirm(L('هل تريد فصل حساب ثريدز؟', 'Disconnect your Threads account?'))) return;
    const s = document.getElementById('conn-status');
    try {
        await fetch('/api/threads/disconnect', { method: 'POST' });
        s.textContent = L('تم فصل ثريدز.', 'Threads disconnected.');
        s.style.color = '#059669';
    } catch (e) {
        s.textContent = L('تعذر الفصل.', 'Could not disconnect.');
        s.style.color = '#dc2626';
    }
    loadConnections();
}

// ---- password ------------------------------------------------------------
async function changePassword() {
    const s = document.getElementById('pw-status');
    const cur = document.getElementById('pw-current').value;
    const nw = document.getElementById('pw-new').value;
    const cf = document.getElementById('pw-confirm').value;
    const fail = m => { s.textContent = '❌ ' + m; s.style.color = '#dc2626'; };
    if (!cur || !nw) return fail(L('املأ كل الحقول.', 'Fill in all fields.'));
    if (nw.length < 8) return fail(L('كلمة المرور الجديدة يجب ألا تقل عن 8 أحرف.',
                                     'The new password must be at least 8 characters.'));
    if (nw !== cf) return fail(L('كلمتا المرور غير متطابقتين.', 'The passwords do not match.'));
    try {
        const r = await fetch('/auth/change-password', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ current_password: cur, new_password: nw })
        });
        const d = await r.json();
        if (!r.ok) return fail(d.detail || L('فشل التغيير.', 'The change failed.'));
        s.textContent = '✅ ' + L('تم تغيير كلمة المرور.', 'Password changed.');
        s.style.color = '#059669';
        ['pw-current', 'pw-new', 'pw-confirm'].forEach(i => { document.getElementById(i).value = ''; });
    } catch (e) {
        fail(L('تعذر الاتصال بالخادم.', 'Could not reach the server.'));
    }
}

async function signOut() {
    try { await fetch('/auth/logout', { method: 'POST' }); } catch (e) {}
    window.location.href = '/login';
}

// ---- boot ----------------------------------------------------------------
function paintAll() {
    paintStaticLabels();
    paintBanner();
    loadSubscription();
    loadAi();
    loadConnections();
}
document.addEventListener('DOMContentLoaded', paintAll);
window.addEventListener('hudhud_lang_change', paintAll);
</script>
</body>
</html>"""


module_registry.register_module(
    name="account_page",
    description="Customer account page /account: subscription, AI master switch, "
                "connected channels (connect/disconnect), password, sign out",
    register_router=register,
    pages=[PageSpec(path="/account", template="account", access=ACCESS_USER)],
    nav=[NavEntry(href="/account", label_key="nav.account", icon="👤",
                  section="nav.account", order=1)],
)

"""
Billing pages module (Phase 9) — customer-facing checkout flow pages.

/billing/success   → Polar returns here after payment. Polls the subscription
                     until entitlements sync (webhook-driven), then routes to
                     onboarding step 3 with connect buttons unlocked.
/billing/checkout-page → the "Subscribe to a plan" destination from the
                     wizard's subscription wall: plan composer with live quote
                     (geo-aware), coupon input, and Polar checkout redirect.
"""
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

from src.core.modules import module_registry, NavEntry

_SUCCESS_HTML = """<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Hudhud — Payment successful</title>
<link rel="icon" href="/static/favicon.ico" sizes="any">
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&family=Tajawal:wght@400;700&display=swap" rel="stylesheet">
<style>
:root{--bg-page:#f8fafc;--bg-card:#fff;--border-default:#e2e8f0;--text-primary:#0f172a;--text-secondary:#475569;--text-muted:#94a3b8;--primary:#2563eb;--green:#059669;}
*{margin:0;box-sizing:border-box;}
body{font-family:'Plus Jakarta Sans','Tajawal',sans-serif;background:var(--bg-page);color:var(--text-primary);min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px;}
.card{background:var(--bg-card);border:1px solid var(--border-default);border-radius:20px;padding:44px 40px;max-width:480px;width:100%;text-align:center;}
.icon{font-size:52px;margin-bottom:12px;}
h1{font-size:22px;margin-bottom:8px;}
.sub{font-size:13.5px;color:var(--text-secondary);line-height:1.7;margin-bottom:20px;}
.status{background:#f1f5f9;border-radius:10px;padding:12px 16px;font-size:12.5px;color:var(--text-secondary);margin-bottom:22px;line-height:1.7;}
.spin{display:inline-block;animation:sp 1.2s linear infinite;}
@keyframes sp{to{transform:rotate(360deg);}}
.btn{display:block;width:100%;background:var(--primary);color:#fff;border:none;border-radius:12px;padding:13px;font-size:14px;font-weight:800;cursor:pointer;font-family:inherit;}
.note{font-size:11.5px;color:var(--text-muted);margin-top:14px;}
</style>
</head>
<body>
<div class="card">
    <div class="icon" id="icon">✅</div>
    <h1 id="title">Payment received — thank you!</h1>
    <div class="sub" id="sub">Your platforms are being activated right now. This usually takes a few seconds.</div>
    <div class="status" id="status"><span class="spin">⏳</span> Activating your platforms…</div>
    <button class="btn" id="continueBtn" style="display:none;" onclick="window.location.href='/onboarding?step=3'">Continue → Connect your platforms</button>
    <div class="note">Polar · secure checkout · hudhd.com</div>
</div>
<script>
let polls = 0;
async function poll() {
    polls++;
    try {
        const r = await fetch('/api/billing/subscription');
        const d = await r.json();
        if (d.platforms && d.platforms.length > 0) {
            document.getElementById('status').innerHTML = '✅ Activated platforms: <strong>' + d.platforms.join(', ') + '</strong>';
            document.getElementById('continueBtn').style.display = 'block';
            document.getElementById('sub').textContent = 'All set! Your connected platforms are unlocked in your workspace.';
            return;
        }
        if (d.status === 'active') {  // subscription active but platforms sync pending
            document.getElementById('status').innerHTML = '<span class="spin">⏳</span> Finalizing platform sync…';
        }
    } catch (e) { /* silent */ }
    if (polls < 20) setTimeout(poll, 2500);
    else {
        document.getElementById('status').textContent = 'Still syncing — you can continue; platforms unlock automatically once confirmed.';
        document.getElementById('continueBtn').style.display = 'block';
    }
}
document.addEventListener('DOMContentLoaded', () => {
    const isAr = localStorage.getItem('hudhud_lang') === 'ar';
    if (isAr) {
        document.getElementById('title').textContent = 'تم استلام الدفعة — شكراً لك!';
        document.getElementById('sub').textContent = 'منصاتك بتتفعل الآن — عادة بياخد ثواني.';
        document.getElementById('continueBtn').textContent = 'متابعة → اربط منصاتك';
        document.getElementById('note').textContent = 'Polar · دفع آمن · hudhd.com';
    }
    poll();
});
</script>
</body>
</html>"""

_CHECKOUT_HTML = """<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Hudhud — Choose your platforms</title>
<link rel="icon" href="/static/favicon.ico" sizes="any">
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&family=Tajawal:wght@400;700&display=swap" rel="stylesheet">
<style>
:root{--bg-page:#f8fafc;--bg-card:#fff;--border-default:#e2e8f0;--text-primary:#0f172a;--text-secondary:#475569;--text-muted:#94a3b8;--primary:#2563eb;--green:#059669;}
*{margin:0;box-sizing:border-box;}
body{font-family:'Plus Jakarta Sans','Tajawal',sans-serif;background:var(--bg-page);color:var(--text-primary);min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px;}
.card{background:var(--bg-card);border:1px solid var(--border-default);border-radius:20px;padding:36px;max-width:560px;width:100%;}
h1{font-size:21px;margin-bottom:6px;}
.sub{font-size:13px;color:var(--text-secondary);margin-bottom:22px;}
.plat{display:flex;align-items:center;gap:12px;border:2px solid var(--border-default);border-radius:14px;padding:14px 16px;margin-bottom:10px;cursor:pointer;transition:.15s;}
.plat:hover{border-color:var(--primary);}
.plat.sel{border-color:var(--primary);background:#eff6ff;}
.plat .nm{font-weight:700;font-size:14px;}
.plat .ds{font-size:12px;color:var(--text-muted);}
.plat .pr{margin-inline-start:auto;font-weight:800;font-size:15px;}
.plat input{width:19px;height:19px;accent-color:var(--primary);cursor:pointer;}
.disc{background:#ecfdf5;border:1px solid #a7f3d0;color:#047857;border-radius:10px;padding:8px 12px;font-size:12px;font-weight:700;margin:12px 0;}
.totrow{display:flex;justify-content:space-between;align-items:center;padding:14px 4px;border-top:2px solid var(--border-default);margin-top:14px;}
.tot{font-size:15px;font-weight:800;}
.coup{display:flex;gap:8px;margin:14px 0;}
.coup input{flex:1;padding:9px 12px;border:1px solid var(--border-default);border-radius:9px;font-family:inherit;font-size:13px;text-transform:uppercase;}
.btn{width:100%;background:var(--primary);color:#fff;border:none;border-radius:12px;padding:14px;font-size:15px;font-weight:800;cursor:pointer;font-family:inherit;margin-top:8px;}
.btn:disabled{opacity:.5;cursor:not-allowed;}
.secure{font-size:11.5px;color:var(--text-muted);text-align:center;margin-top:12px;}
.trial{background:#eff6ff;border:1px solid #bfdbfe;color:#1d4ed8;border-radius:10px;padding:10px 14px;font-size:12.5px;font-weight:600;margin-bottom:16px;cursor:pointer;}
</style>
</head>
<body>
<div class="card">
    <h1 id="ttl">Choose your platforms</h1>
    <div class="sub" id="sbt">Pay only for what you use. Add or remove platforms anytime — multi-platform discounts apply automatically.</div>
    <button class="trial" id="trialBtn" onclick="startTrial()">🎁 Try ALL platforms free for 3 days (card required)</button>
    <div id="platforms"></div>
    <div class="disc" id="disc-box" style="display:none;"></div>
    <div class="coup">
        <input id="coupon" placeholder="Coupon code (optional)">
    </div>
    <div class="totrow"><span id="totlbl" style="color:var(--text-secondary);font-size:13.5px;">Total / month</span><span class="tot" id="total">$0</span></div>
    <button class="btn" id="payBtn" onclick="pay()" disabled>Continue to secure payment →</button>
    <div class="secure">🔒 Powered by Polar · hudhd.com</div>
</div>
<script>
let sel = new Set();
const CATALOG = [];   // filled from API

async function init() {
    const isAr = localStorage.getItem('hudhud_lang') === 'ar';
    if (isAr) {
        document.getElementById('ttl').textContent = 'اختر منصاتك';
        document.getElementById('sbt').textContent = 'ادفع مقابل اللي بتستخدمه بس. ضيف أو شيل منصات في أي وقت — وخصومات المنصات المتعددة تُطبق تلقائياً.';
        document.getElementById('trialBtn').textContent = '🎁 جرّب كل المنصات مجاناً 3 أيام (ببطاقة)';
        document.getElementById('totlbl').textContent = 'الإجمالي / شهرياً';
        document.getElementById('coupon').placeholder = 'كود خصم (اختياري)';
        document.getElementById('payBtn').textContent = 'المتابعة للدفع الآمن ←';
        document.getElementById('secure').textContent = '🔒 عبر Polar · hudhd.com';
    }
    const r = await fetch('/api/billing/catalog-public');
    const d = await r.json();
    CATALOG.push(...(d.catalog || []));
    render();
}

function render() {
    const box = document.getElementById('platforms');
    box.innerHTML = CATALOG.filter(c => c.is_available).map(c => `
        <div class="plat ${sel.has(c.platform) ? 'sel' : ''}" onclick="toggleSel('${c.platform}')">
            <input type="checkbox" ${sel.has(c.platform) ? 'checked' : ''} onclick="event.stopPropagation();toggleSel('${c.platform}')">
            <div style="width:34px;height:34px;border-radius:9px;overflow:hidden;flex-shrink:0;">${window.platformIcon(c.platform, 34)}</div>
            <div style="flex:1;"><div class="nm">${c.display_name}</div><div class="ds">${c.platform === 'facebook' ? 'Messages, comments, publishing & insights' : c.platform === 'instagram' ? 'DMs, comments, publishing & insights' : 'Publishing & replies'}</div></div>
            <div class="pr">$${c.price_usd}<span style="font-size:10px;color:var(--text-muted);">/mo</span></div>
        </div>`).join('');
    updateTotals();
}

function toggleSel(p) {
    if (sel.has(p)) sel.delete(p); else sel.add(p);
    render();
}

async function updateTotals() {
    const payBtn = document.getElementById('payBtn');
    if (sel.size === 0) { document.getElementById('total').textContent = '$0'; payBtn.disabled = true; return; }
    const code = document.getElementById('coupon').value.trim();
    try {
        const r = await fetch(`/api/billing/quote?platforms=${[...sel].join(',')}${code ? '&coupon=' + encodeURIComponent(code) : ''}`);
        const q = await r.json();
        document.getElementById('total').textContent = '$' + q.total_usd;
        const disc = document.getElementById('disc-box');
        if (q.multi_platform_discount_percent > 0 || q.coupon_discount_usd > 0) {
            disc.style.display = 'block';
            let txt = [];
            if (q.multi_platform_discount_percent > 0) txt.push(`${q.multi_platform_discount_percent}% multi-platform discount applied`);
            if (q.coupon_discount_usd > 0) txt.push(`Coupon −$${q.coupon_discount_usd}`);
            disc.textContent = '✓ ' + txt.join(' · ');
        } else disc.style.display = 'none';
        payBtn.disabled = false;
    } catch (e) { payBtn.disabled = true; }
}

async function pay() {
    const payBtn = document.getElementById('payBtn');
    payBtn.disabled = true; payBtn.textContent = '⏳ Redirecting to secure checkout…';
    try {
        const code = document.getElementById('coupon').value.trim();
        const r = await fetch('/api/billing/checkout', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ platforms: [...sel], coupon: code || null })
        });
        const d = await r.json();
        if (r.ok && d.checkout_url) window.location.href = d.checkout_url;
        else { alert(d.detail || 'Checkout failed'); payBtn.disabled = false; payBtn.textContent = 'Continue to secure payment →'; }
    } catch (e) { alert('Connection error'); payBtn.disabled = false; }
}

async function startTrial() {
    const btn = document.getElementById('trialBtn');
    btn.textContent = '⏳ Redirecting…'; btn.disabled = true;
    try {
        const r = await fetch('/api/billing/trial', { method: 'POST' });
        const d = await r.json();
        if (r.ok && d.checkout_url) window.location.href = d.checkout_url;
        else { alert(d.detail || 'Trial unavailable'); btn.disabled = false; }
    } catch (e) { alert('Connection error'); btn.disabled = false; }
}

document.addEventListener('DOMContentLoaded', init);
</script>
</body>
</html>"""


def register(app: FastAPI) -> None:
    @app.get("/billing/success", include_in_schema=False)
    async def billing_success(request: Request):
        return HTMLResponse(content=_SUCCESS_HTML)

    @app.get("/billing/checkout-page", include_in_schema=False)
    async def billing_checkout_page(request: Request):
        return HTMLResponse(content=_CHECKOUT_HTML)


module_registry.register_module(
    name="billing_pages",
    description="Customer checkout flow pages: plan composer with live quote + payment success (entitlement sync poll)",
    register_router=register,
)

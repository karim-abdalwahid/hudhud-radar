"""Customer-owned account controls.

The platform operator's ``/settings`` remains an admin console.  This module
exposes only actions that are already enforced against the signed-in user's
``user_id``: subscription status, AI pause, owned channel connections, password
rotation, and session logout.
"""
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

from src.core.modules import ACCESS_USER, NavEntry, PageSpec, module_registry


def register(app: FastAPI) -> None:
    @app.get("/account", include_in_schema=False)
    async def account_page(request: Request):
        from src.modules.pages import render_module_page
        return render_module_page(_ACCOUNT_HTML, request)


_ACCOUNT_HTML = r"""<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Hudhud — My Account</title>
<link rel="icon" href="/static/favicon.ico" sizes="any">
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Tajawal:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/static/saas.css">
<style>
.acct-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:14px}
.acct-card{background:var(--bg-card);border:1px solid var(--border-default);border-radius:14px;padding:18px}
.acct-card h3{font-size:15px;font-weight:700;margin:0 0 4px;display:flex;align-items:center;gap:8px}
.acct-desc{font-size:12.5px;color:var(--text-muted);line-height:1.6;margin-bottom:14px}
.acct-row{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:11px 0;border-bottom:1px solid var(--border-default);flex-wrap:wrap}
.acct-row:last-child{border-bottom:none}.acct-name{font-size:13.5px;font-weight:600}.acct-sub{font-size:11.5px;color:var(--text-muted);margin-top:2px}
.pill{font-size:11.5px;font-weight:700;padding:4px 11px;border-radius:99px;display:inline-block}.pill-on{background:#ecfdf5;color:#059669}.pill-off{background:#fef2f2;color:#dc2626}.pill-warn{background:#fffbeb;color:#b45309}.pill-mut{background:var(--bg-subtle);color:var(--text-muted)}
.btn-sm{padding:7px 14px;font-size:12.5px;font-weight:700;border-radius:8px;cursor:pointer;border:1px solid var(--border-default);background:var(--bg-card);color:var(--text-primary);font-family:inherit}.btn-sm:hover{border-color:var(--text-muted)}.btn-danger{border-color:#dc2626;color:#dc2626}.btn-danger:hover{background:#fef2f2}.btn-sm:disabled{opacity:.5;cursor:not-allowed}
.acct-field{margin-bottom:11px}.acct-field label{display:block;font-size:12px;font-weight:600;color:var(--text-secondary);margin-bottom:4px}.acct-field input{width:100%;padding:10px 12px;border-radius:10px;border:1px solid var(--border-default);background:var(--bg-subtle);color:var(--text-primary);font-family:inherit;font-size:13px}.acct-status{font-size:12.5px;min-height:18px;margin-top:8px}.acct-empty{font-size:12.5px;color:var(--text-muted);padding:14px 0;text-align:center}.acct-link{text-decoration:none;display:inline-block}
</style>
</head>
<body>
<div class="app-layout">
  <aside class="app-sidebar">
    <div class="sidebar-header"><a href="/dashboard" class="brand-logo-link"><span class="brand-logo-text">Hudhud</span><span class="brand-dot">.</span></a><div class="brand-sub" data-i18n="brand.tagline">Autonomous AI Social Sales Agent</div></div>
    <nav class="sidebar-nav"></nav>
    <div class="sidebar-footer"><div id="meta-status-container" class="status-pill"><div id="meta-dot" class="status-dot"></div><span id="meta-status-badge" data-i18n="status.checking">Checking status...</span></div></div>
  </aside>
  <main class="app-main">
    <header class="app-topbar"><div class="topbar-breadcrumb"><span class="crumb-root">Hudhud</span><span class="crumb-sep">/</span><span class="crumb-current" id="crumb-account">My Account</span></div><div class="topbar-actions"><button type="button" class="lang-switcher-btn" id="language-toggle"><span data-i18n="lang.switch_btn">🌐 العربية</span></button></div></header>
    <div class="app-content"><div id="acct-banner"></div><div class="acct-grid">
      <section class="acct-card"><h3>💳 <span id="h-sub"></span></h3><div class="acct-desc" id="d-sub"></div><div id="sub-body" class="acct-empty">…</div></section>
      <section class="acct-card"><h3>🤖 <span id="h-ai"></span></h3><div class="acct-desc" id="d-ai"></div><div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap"><span class="pill pill-mut" id="ai-badge">…</span><button type="button" class="btn-sm" id="btn-ai">…</button></div><div class="acct-status" id="ai-status"></div></section>
      <section class="acct-card" style="grid-column:1/-1"><h3>🔗 <span id="h-conn"></span></h3><div class="acct-desc" id="d-conn"></div><div id="conn-body" class="acct-empty">…</div><div class="acct-status" id="conn-status"></div></section>
      <section class="acct-card"><h3>🔐 <span id="h-pw"></span></h3><div class="acct-desc" id="d-pw"></div><div style="max-width:420px"><div class="acct-field"><label id="l-pw-cur"></label><input type="password" id="pw-current" autocomplete="current-password"></div><div class="acct-field"><label id="l-pw-new"></label><input type="password" id="pw-new" autocomplete="new-password"></div><div class="acct-field"><label id="l-pw-cf"></label><input type="password" id="pw-confirm" autocomplete="new-password"></div><button type="button" class="btn-sm" id="btn-pw">…</button><div class="acct-status" id="pw-status"></div></div></section>
      <section class="acct-card"><h3>👤 <span id="h-id"></span></h3><div class="acct-desc" id="d-id"></div><div class="acct-row"><div><div class="acct-name" id="acct-email">…</div><div class="acct-sub" id="s-email"></div></div></div><div class="acct-row"><div><div class="acct-name" id="l-signout"></div><div class="acct-sub" id="s-signout"></div></div><button type="button" class="btn-sm" id="btn-signout">…</button></div></section>
    </div></div>
  </main>
</div>
<script src="/static/i18n.js"></script>
<script src="/static/saas.js"></script>
<script>
const PLATFORM = {facebook:{ar:'فيسبوك',en:'Facebook',icon:'📘'},instagram:{ar:'إنستجرام',en:'Instagram',icon:'📸'},threads:{ar:'ثريدز',en:'Threads',icon:'🧵'}};
function isAr(){return !!(window.hudhudI18n&&window.hudhudI18n.currentLang==='ar')}
function L(ar,en){return isAr()?ar:en}
function $id(id){return document.getElementById(id)}
function setText(id,ar,en){const el=$id(id);if(el)el.textContent=L(ar,en)}
function setStatus(id,text,ok){const el=$id(id);el.textContent=text;el.style.color=ok?'#059669':'#dc2626'}
function named(platform){const item=PLATFORM[platform];return item?L(item.ar,item.en):String(platform||'')}
function element(tag, className, text){const el=document.createElement(tag);if(className)el.className=className;if(text!==undefined)el.textContent=text;return el}
async function jsonRequest(url, options){const response=await fetch(url,options);let data={};try{data=await response.json()}catch(_e){}if(!response.ok)throw new Error(data.detail||'request_failed');return data}

function paintLabels(){
  document.title=L('هدهد — حسابي','Hudhud — My Account');setText('crumb-account','حسابي','My Account');setText('h-sub','الاشتراك والخطة','Subscription & plan');setText('d-sub','حالة اشتراكك والمنصات المتاحة في خطتك الحالية.','Your subscription status and the platforms included in your current plan.');setText('h-ai','مفتاح الردود الآلية','AI master switch');setText('d-ai','أوقف الذكاء الاصطناعي عبر كل محادثاتك وتعليقاتك لتدير حساباتك بنفسك. الرسائل الجديدة تظل تظهر في صندوق الوارد للرد اليدوي.','Pause AI across your conversations and comment automations. New messages still arrive in your inbox for manual replies.');setText('h-conn','الحسابات المربوطة','Connected channels');setText('d-conn','فصل أي قناة يوقف ردود الوكيل عليها فوراً ولا يحذف بياناتك أو محادثاتك السابقة.','Disconnecting a channel stops the agent replying there immediately; it does not delete your data or past conversations.');setText('h-pw','تغيير كلمة المرور','Change password');setText('d-pw','التغيير فوري ويتطلب كلمة المرور الحالية.','The change is instant and requires your current password.');setText('l-pw-cur','كلمة المرور الحالية','Current password');setText('l-pw-new','كلمة المرور الجديدة (8 أحرف على الأقل)','New password (8+ characters)');setText('l-pw-cf','تأكيد كلمة المرور الجديدة','Confirm new password');setText('btn-pw','💾 حفظ كلمة المرور','💾 Save password');setText('h-id','بيانات الحساب','Account details');setText('d-id','الحساب المستخدم لتسجيل الدخول لهذه المنصة.','The account you use to sign in to this platform.');setText('s-email','البريد الإلكتروني','Email address');setText('l-signout','تسجيل الخروج','Sign out');setText('s-signout','إنهاء الجلسة على هذا الجهاز','End the session on this device');setText('btn-signout','خروج','Sign out');
}

function paintBanner(){const q=new URLSearchParams(location.search), box=$id('acct-banner');box.replaceChildren();let message='', success=false;if(q.get('connected')){message=L('تم ربط '+named(q.get('connected'))+' بنجاح.',''+named(q.get('connected'))+' connected successfully.');success=true}else if(q.get('threads')==='connected'){message=L('تم ربط ثريدز بنجاح.','Threads connected successfully.');success=true}else if(q.get('connect_error')||q.get('threads')==='error'){const reason=q.get('connect_error');message=reason==='invalid_state'?L('انتهت صلاحية طلب الربط. حاول مرة أخرى.','The connect request expired. Please try again.'):reason==='no_pages'?L('لا توجد صفحات مُدارة على هذا الحساب.','No managed Pages were found on that account.'):L('فشل الربط. حاول مرة أخرى أو تواصل معنا.','Connection failed. Please try again or contact us.')}if(message){const card=element('div','acct-card');card.style.cssText='border-color:'+(success?'#059669':'#dc2626')+';margin-bottom:14px';const line=element('div','', (success?'✅ ':'❌ ')+message);line.style.cssText='color:'+(success?'#059669':'#dc2626')+';font-weight:700;font-size:13.5px';card.append(line);box.append(card);history.replaceState({},'', '/account')}}

async function loadSubscription(){const box=$id('sub-body');try{const d=await jsonRequest('/api/billing/subscription');const status=d.status||'none', labels={active:L('اشتراك نشط','Active'),trialing:L('تجربة مجانية','Free trial'),canceled:L('منتهي','Canceled'),none:L('لا يوجد اشتراك','No subscription')}, cls=status==='active'?'pill-on':status==='trialing'?'pill-warn':'pill-off';box.className='';box.replaceChildren();const row1=element('div','acct-row'),left=element('div'),name=element('div','acct-name',L('الحالة','Status')),note=element('div','acct-sub');if(d.trial_ends_at)note.textContent=L('تنتهي التجربة في ','Trial ends: ')+String(d.trial_ends_at).slice(0,16).replace('T',' ');left.append(name,note);row1.append(left,element('span','pill '+cls,labels[status]||status));const row2=element('div','acct-row'),plan=element('div'),planName=element('div','acct-name',L('المنصات في خطتك','Platforms in your plan')),planSub=element('div','acct-sub',(d.platforms||[]).map(p=>(PLATFORM[p]?PLATFORM[p].icon+' '+named(p):String(p))).join(' · ')||L('لا توجد منصات مفعّلة','No platforms enabled yet')),link=element('a','btn-sm acct-link',status==='active'?L('تعديل الخطة','Change plan'):L('اشترك الآن','Subscribe'));link.href='/billing/checkout-page';plan.append(planName,planSub);row2.append(plan,link);box.append(row1,row2)}catch(_e){box.textContent=L('تعذر تحميل بيانات الاشتراك.','Could not load subscription details.')}}

function renderAi(d){const effective=!!d.effective_paused, globallyPaused=!!d.global_paused&&!d.user_paused, badge=$id('ai-badge'),btn=$id('btn-ai');badge.textContent=effective?L('⏸️ موقوف','⏸️ Paused'):L('✅ نشط','✅ Active');badge.className='pill '+(effective?'pill-off':'pill-on');btn.disabled=globallyPaused;btn.textContent=effective?L('▶️ تشغيل الردود الآلية','▶️ Resume AI replies'):L('⏸️ إيقاف الردود الآلية','⏸️ Pause AI replies');btn.className='btn-sm'+(effective?'':' btn-danger');const note=$id('ai-status');note.style.color='var(--text-muted)';note.textContent=globallyPaused?L('موقوف على مستوى المنصة بواسطة الإدارة.','Paused platform-wide by the operator.'):''}
async function loadAi(){try{renderAi(await jsonRequest('/api/ai/pause'))}catch(_e){$id('ai-badge').textContent=L('غير متاح','Unavailable')}}
async function toggleAi(){const btn=$id('btn-ai');btn.disabled=true;try{const state=await jsonRequest('/api/ai/pause');if(state.global_paused&&!state.user_paused){renderAi(state);return}renderAi(await jsonRequest('/api/ai/pause',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({paused:!state.user_paused})}))}catch(_e){setStatus('ai-status',L('تعذر تغيير الحالة.','Could not change the state.'),false)}finally{if(!$id('ai-status').textContent.includes(L('موقوف على مستوى','Paused platform-wide')))btn.disabled=false}}

function connectionRow(connection){const row=element('div','acct-row'), left=element('div'), p=PLATFORM[connection.platform]||{icon:'🔗'}, title=element('div','acct-name',p.icon+' '+named(connection.platform)), detail=element('div','acct-sub',connection.account_name||connection.account_id||''), controls=element('div','');controls.style.cssText='display:flex;gap:8px;align-items:center';controls.append(element('span','pill pill-on',L('متصل','Connected')));const button=element('button','btn-sm btn-danger',L('فصل','Disconnect'));button.type='button';button.addEventListener('click',()=>disconnect(connection.platform,connection.account_name||connection.platform));controls.append(button);left.append(title,detail);row.append(left,controls);return row}
function threadsConnectRow(configured){const row=element('div','acct-row'),left=element('div'),title=element('div','acct-name','🧵 '+named('threads')),detail=element('div','acct-sub',configured?L('خدمة ثريدز مفعّلة في خطتك.','Threads is enabled in your plan.'):L('ثريدز غير مهيأ على المنصة بعد.','Threads is not configured on the platform yet.')),controls=element('div','');controls.style.cssText='display:flex;gap:8px;align-items:center';const button=element('button','btn-sm',L('ربط','Connect'));button.type='button';button.disabled=!configured;button.addEventListener('click',connectThreads);controls.append(button);left.append(title,detail);row.append(left,controls);return row}
function connectLink(text){const wrap=element('div','');wrap.style.marginTop='12px';const link=element('a','btn-sm acct-link',text);link.href='/onboarding';wrap.append(link);return wrap}
async function loadConnections(){const box=$id('conn-body');try{const overview=await jsonRequest('/api/connections'),connections=(overview.connections||[]).filter(c=>c&&c.platform);let threads={configured:false,connected:false};try{threads=await jsonRequest('/api/threads/status')}catch(_e){}box.replaceChildren();box.className='';connections.forEach(c=>box.append(connectionRow(c)));const threadsEnabled=(overview.paid_platforms||[]).includes('threads');if(threadsEnabled&&!connections.some(c=>c.platform==='threads'))box.append(threadsConnectRow(!!threads.configured));if(!box.childElementCount){box.className='acct-empty';box.append(document.createTextNode(L('لا توجد قنوات مربوطة بعد.','No channels connected yet.')))}box.append(connectLink(connections.length?'+ '+L('ربط قناة أخرى','Connect another channel'):L('اربط قناتك الأولى','Connect your first channel')))}catch(_e){box.textContent=L('تعذر تحميل الحسابات.','Could not load your channels.')}}
async function connectThreads(){try{const data=await jsonRequest('/api/threads/oauth/authorize');if(data.authorize_url)window.location.href=data.authorize_url;else throw new Error('missing_authorize_url')}catch(_e){setStatus('conn-status',L('تعذر بدء ربط ثريدز.','Could not start the Threads connection.'),false)}}
async function disconnect(platform,label){const warning=L('سيتوقف الوكيل عن الرد على "'+label+'" فوراً. بياناتك ومحادثاتك السابقة تبقى كما هي. متابعة؟','The agent will stop replying on "'+label+'" immediately. Your data and past conversations stay intact. Continue?');if(!window.confirm(warning))return;try{await jsonRequest('/api/connections/'+encodeURIComponent(platform),{method:'DELETE'});setStatus('conn-status',L('تم فصل القناة.','Channel disconnected.'),true);await loadConnections()}catch(_e){setStatus('conn-status',L('تعذر فصل القناة. حاول مرة أخرى.','Could not disconnect. Please try again.'),false)}}

async function changePassword(){const current=$id('pw-current').value,next=$id('pw-new').value,confirmPassword=$id('pw-confirm').value;if(!current||!next||!confirmPassword)return setStatus('pw-status',L('املأ كل الحقول.','Fill in all fields.'),false);if(next.length<8)return setStatus('pw-status',L('كلمة المرور الجديدة يجب ألا تقل عن 8 أحرف.','The new password must be at least 8 characters.'),false);if(next!==confirmPassword)return setStatus('pw-status',L('كلمتا المرور غير متطابقتين.','The passwords do not match.'),false);try{await jsonRequest('/auth/change-password',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({current_password:current,new_password:next})});['pw-current','pw-new','pw-confirm'].forEach(id=>$id(id).value='');setStatus('pw-status',L('تم تغيير كلمة المرور.','Password changed.'),true)}catch(_e){setStatus('pw-status',L('تعذر تغيير كلمة المرور. تأكد من كلمة المرور الحالية.','Could not change the password. Check your current password.'),false)}}
async function loadIdentity(){try{const me=await jsonRequest('/auth/me');$id('acct-email').textContent=me.email||L('لا توجد بيانات','No account data')}catch(_e){$id('acct-email').textContent=L('تعذر تحميل الحساب','Could not load account')}}
async function signOut(){try{await fetch('/auth/logout',{method:'POST'})}finally{window.location.href='/login'}}
async function loadAll(){paintLabels();paintBanner();await Promise.all([loadSubscription(),loadAi(),loadConnections(),loadIdentity()])}
document.addEventListener('DOMContentLoaded',()=>{const lang=$id('language-toggle');lang.addEventListener('click',()=>window.hudhudI18n&&window.hudhudI18n.toggle());$id('btn-ai').addEventListener('click',toggleAi);$id('btn-pw').addEventListener('click',changePassword);$id('btn-signout').addEventListener('click',signOut);loadAll()});window.addEventListener('hudhud_lang_change',loadAll);
</script>
</body>
</html>"""


module_registry.register_module(
    name="account_page",
    description="Customer account page: subscription, AI pause, owned connections, password, and logout",
    register_router=register,
    pages=[PageSpec(path="/account", template="account", access=ACCESS_USER)],
    nav=[NavEntry(href="/account", label_key="nav.account", icon="👤",
                  section="nav.account", order=1)],
)

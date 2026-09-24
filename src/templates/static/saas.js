// HudhudRadar / Hudhud — Unified SaaS Common Client JS
// Provides: System Health Polling, Meta Status, and Client vs Developer Role Separation

let lastMetaData = null;

const hudhudRoleManager = {
    // Admin-only surfaces (server 403s non-admins). Client View hides ALL of
    // them; Dev Console shows them and hides client workspace sections.
    DEV_ROUTES: ['/settings', '/users', '/templates'],
    _isAdmin: false,

    isDevRoute() {
        const currentPath = window.location.pathname;
        return this.DEV_ROUTES.some(r => currentPath === r || currentPath.startsWith(r + '/'));
    },

    getMode() {
        const saved = localStorage.getItem('hudhud_role_mode');
        if (saved === 'client' || saved === 'developer') return saved;
        return this.isDevRoute() ? 'developer' : 'client';
    },

    setMode(mode) {
        localStorage.setItem('hudhud_role_mode', mode);
        // Mirror to a cookie so the SERVER renders the correct initial mode
        // (zero flash on next loads — Wave 9.8).
        document.cookie = `hudhud_role_mode=${mode};path=/;max-age=31536000;SameSite=Lax`;
        this.applyMode(mode);

        if (mode === 'client' && this.isDevRoute()) {
            window.location.href = '/dashboard';
        }
    },

    applyMode(mode) {
        document.body.classList.remove('mode-client', 'mode-developer');
        document.body.classList.add(mode === 'developer' ? 'mode-developer' : 'mode-client');

        const btnClient = document.getElementById('hudhud-btn-client');
        const btnDev = document.getElementById('hudhud-btn-dev');

        if (btnClient && btnDev) {
            btnClient.classList.toggle('active', mode === 'client');
            btnDev.classList.toggle('active', mode === 'developer');
        }

        window.dispatchEvent(new CustomEvent('hudhud_role_change', { detail: { mode } }));
    },

    normalizeBrandLogo() {
        const header = document.querySelector('.sidebar-header');
        if (header) {
            const existingLink = header.querySelector('.brand-logo-link');
            if (!existingLink) {
                const isAr = window.hudhudI18n && window.hudhudI18n.currentLang === 'ar';
                header.innerHTML = `
                    <a href="/dashboard" class="brand-logo-link">
                        <span class="brand-logo-text">Hudhud</span><span class="brand-dot">.</span>
                    </a>
                    <div class="brand-sub" data-i18n="brand.tagline">${isAr ? 'وكيل المبيعات الذكي والتواصل التلقائي' : 'Autonomous AI Social Sales Agent'}</div>
                `;
            }
        }
    },

    async init() {
        // The SERVER already rendered the correct structure: body carries the
        // initial mode class and the sidebar ships pre-separated into
        // .client-nav-section / .dev-nav-section — zero first-paint flash.

        // 1. Resolve the REAL role from the server session.
        try {
            const res = await fetch('/auth/me');
            const me = await res.json();
            this._isAdmin = !!(me && me.authenticated && me.role === 'admin');
        } catch (e) {
            this._isAdmin = false;
        }

        this.normalizeBrandLogo();

        // 2. Non-admins: no role switcher. The server already excluded admin
        //    links from their sidebar (registry admin_only filter).
        if (!this._isAdmin) {
            document.body.classList.remove('mode-developer');
            document.body.classList.add('mode-client');
            return;
        }

        // 3. Admin: honor the saved/cookie mode; on a dev route in client mode
        //    → enforce real separation (redirect, same as setMode).
        const saved = localStorage.getItem('hudhud_role_mode');
        if (this.isDevRoute() && saved === 'client') {
            window.location.href = '/dashboard';
            return;
        }

        this.injectRoleSwitcher();
        this.injectDevPageBanner();
    },

    stripDevNav() {
        // Removes developer-only links (server returns 403 for non-admins).
        const nav = document.querySelector('.sidebar-nav');
        if (!nav) return;
        nav.querySelectorAll('a.nav-item').forEach(a => {
            const href = (a.getAttribute('href') || '').split('?')[0];
            if (this.DEV_ROUTES.some(r => href === r || href.startsWith(r + '/'))) {
                a.remove();
            }
        });
    },

    injectRoleSwitcher() {
        const sidebar = document.querySelector('.app-sidebar');
        if (!sidebar || document.querySelector('.role-mode-switcher')) return;

        const header = sidebar.querySelector('.sidebar-header');
        if (!header) return;

        const isAr = window.hudhudI18n && window.hudhudI18n.currentLang === 'ar';
        const currentMode = this.getMode();

        const switcher = document.createElement('div');
        switcher.className = 'role-mode-switcher';
        switcher.innerHTML = `
            <button type="button" class="role-btn ${currentMode === 'client' ? 'active' : ''}" id="hudhud-btn-client" onclick="hudhudRoleManager.setMode('client')">
                <span>👤</span> <span data-i18n="mode.client">${isAr ? 'واجهة العميل' : 'Client View'}</span>
            </button>
            <button type="button" class="role-btn ${currentMode === 'developer' ? 'active' : ''}" id="hudhud-btn-dev" onclick="hudhudRoleManager.setMode('developer')">
                <span>🛠️</span> <span data-i18n="mode.developer">${isAr ? 'لوحة المطور' : 'Dev Console'}</span>
            </button>
        `;

        header.insertAdjacentElement('afterend', switcher);

        // NOTE: the sidebar ships PRE-SEPARATED from the server
        // (.client-nav-section / .dev-nav-section) — no client-side grouping.

        // NOTE (WS0.4): sidebar nav links are now rendered SERVER-SIDE from the
        // module registry — the old client-side Automations injection is gone.
    },

    organizeDevNav(sidebar, isAr) {
        const nav = sidebar.querySelector('.sidebar-nav');
        if (!nav) return;

        // If dev-nav-section already exists, return
        if (nav.querySelector('.dev-nav-section')) return;

        // Admin-only links (developer console + owner console pages)
        const devLinks = Array.from(nav.querySelectorAll('a.nav-item')).filter(a => {
            const href = a.getAttribute('href') || '';
            return this.DEV_ROUTES.some(r => href === r || href.startsWith(r + '/') || href.includes(r));
        });

        // Find section title for Analytics & System if present
        const sectionTitles = Array.from(nav.querySelectorAll('.nav-section-title'));
        const sysTitle = sectionTitles.find(t => {
            const i18n = t.getAttribute('data-i18n') || '';
            const txt = t.textContent || '';
            return i18n.includes('analytics') || txt.includes('Analytics') || txt.includes('التحليلات');
        });

        if (devLinks.length > 0) {
            const devSection = document.createElement('div');
            devSection.className = 'dev-nav-section';

            const title = document.createElement('div');
            title.className = 'dev-nav-title';
            title.innerHTML = `
                <span data-i18n="mode.admin_only">${isAr ? 'أدوات المطور والنظام' : 'Developer Console'}</span>
                <span class="dev-badge">ADMIN</span>
            `;
            devSection.appendChild(title);

            if (sysTitle) {
                sysTitle.remove();
            }

            devLinks.forEach(link => devSection.appendChild(link));
            nav.appendChild(devSection);

            // Wrap everything that remains (client workspaces + their section
            // titles) so Developer mode can hide it — TRUE two-way separation.
            const clientWrap = document.createElement('div');
            clientWrap.className = 'client-nav-section';
            Array.from(nav.childNodes).forEach(node => {
                if (node !== devSection) clientWrap.appendChild(node);
            });
            nav.insertBefore(clientWrap, devSection);
        }
    },

    injectDevPageBanner() {
        const currentPath = window.location.pathname;
        const isDevRoute = this.DEV_ROUTES.some(r => currentPath.startsWith(r));
        if (!isDevRoute) return;

        const main = document.querySelector('.app-main');
        if (!main || main.querySelector('.dev-console-banner')) return;

        const isAr = window.hudhudI18n && window.hudhudI18n.currentLang === 'ar';
        const banner = document.createElement('div');
        banner.className = 'dev-console-banner';
        banner.innerHTML = `
            <div style="display: flex; align-items: center; gap: 8px;">
                <span>🛠️</span>
                <span>${isAr ? 'أنت الآن في لوحة تحكم المطور والنظام (صلاحيات المسؤول فقط)' : 'Developer & System Core Console (Admin Only)'}</span>
            </div>
            <button onclick="hudhudRoleManager.setMode('client')" style="background: #ffffff; border: 1px solid #d8b4fe; color: #7e22ce; padding: 3px 10px; border-radius: 6px; font-size: 11px; font-weight: 600; cursor: pointer;">
                ${isAr ? 'التبديل لواجهة العميل →' : 'Switch to Client View →'}
            </button>
        `;

        main.insertBefore(banner, main.firstChild);
    }
};

async function checkSystemMetaStatus() {
    try {
        const res = await fetch('/api/meta/status');
        const data = await res.json();
        lastMetaData = data;
        updateMetaStatusBadge(data);
    } catch (e) {
        console.debug("Status check offline:", e);
    }
}

// Session user chip + logout (injected into sidebar footer)
async function injectSessionUser() {
    try {
        const res = await fetch('/auth/me');
        const me = await res.json();
        if (!me.authenticated) return;

        const sidebar = document.querySelector('.app-sidebar');
        if (!sidebar) return;

        const footer = sidebar.querySelector('.sidebar-footer') || sidebar;
        const existing = document.getElementById('hudhud-user-chip');
        if (existing) return;

        const isAr = window.hudhudI18n && window.hudhudI18n.currentLang === 'ar';
        const displayName = me.full_name || me.email || '';
        const initial = (me.full_name || me.email || '?').trim()[0].toUpperCase();
        const chip = document.createElement('div');
        chip.id = 'hudhud-user-chip';
        chip.style.cssText = 'display:flex;align-items:center;gap:8px;padding:10px 12px;margin-top:8px;border-top:1px solid var(--border-default);';
        chip.innerHTML = `
            <div class="hudhud-avatar" title="${escapeHtml(displayName)}" style="width:32px;height:32px;flex-shrink:0;border-radius:50%;background:var(--accent-blue,#2563eb);color:#fff;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:800;">${escapeHtml(initial)}</div>
            <div style="min-width:0;flex:1;">
                <div style="font-size:12px;font-weight:600;color:var(--text-primary);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${escapeHtml(displayName)}</div>
                <div style="font-size:10.5px;color:var(--text-muted);">${me.role === 'admin' ? (isAr ? 'مدير النظام' : 'Administrator') : (isAr ? 'مستخدم' : 'User')}</div>
            </div>
            <button onclick="hudhudLogout()" title="${isAr ? 'تسجيل الخروج' : 'Sign out'}" style="flex-shrink:0;background:none;border:1px solid var(--border-default);border-radius:8px;padding:6px 10px;cursor:pointer;font-size:13px;color:var(--text-secondary);">⏻</button>
        `;
        footer.appendChild(chip);
    } catch (e) {
        console.debug('Session user check skipped:', e);
    }
}

async function hudhudLogout() {
    try { await fetch('/auth/logout', { method: 'POST' }); } catch (e) { /* ignore */ }
    window.location.href = '/login';
}

function updateMetaStatusBadge(data) {
    if (!data) return;
    const badge = document.getElementById('meta-status-badge');
    const dot = document.getElementById('meta-dot');
    const container = document.getElementById('meta-status-container');
    if (!badge || !dot || !container) return;

    const t = (key) => window.hudhudI18n ? window.hudhudI18n.t(key) : key;

    if (data.token_valid) {
        const pageLabel = data.page_name || data.page_id || "";
        badge.textContent = `${t('status.connected')} (${pageLabel})`;
        badge.style.color = 'var(--badge-green-text)';
        dot.style.background = 'var(--badge-green-text)';
        container.style.borderColor = 'rgba(5, 150, 105, 0.3)';
    } else if (data.configured) {
        badge.textContent = t('status.expired');
        badge.style.color = 'var(--badge-amber-text)';
        dot.style.background = 'var(--badge-amber-text)';
        container.style.borderColor = 'rgba(217, 119, 6, 0.3)';
    } else {
        badge.textContent = t('status.waiting');
        badge.style.color = 'var(--text-muted)';
        dot.style.background = 'var(--text-muted)';
        container.style.borderColor = 'var(--border-default)';
    }
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// --------------------------------------------------------------------
// In-app notifications bell (WS-F) — polls /api/notifications every 60s,
// renders a dropdown from the app-topbar on dashboard pages.
// --------------------------------------------------------------------
let _notifPolling = null;

function getOrCreateTopbarActions(topbar) {
    let actions = topbar.querySelector('.topbar-actions');
    if (!actions) {
        actions = document.createElement('div');
        actions.className = 'topbar-actions';
        topbar.appendChild(actions);
    }
    return actions;
}

function injectNotificationsBell() {
    // Only dashboard pages (topbar exists there); skip landing/auth
    const topbar = document.querySelector('.app-topbar');
    if (!topbar || document.getElementById('hudhud-bell')) return;
    const actions = getOrCreateTopbarActions(topbar);

    const wrap = document.createElement('div');
    wrap.id = 'hudhud-bell';
    wrap.style.cssText = 'position:relative;display:flex;align-items:center;';
    wrap.innerHTML = `
        <button id="hudhud-bell-btn" style="position:relative;background:var(--bg-card);border:1px solid var(--border-default);
            border-radius:10px;padding:7px 11px;cursor:pointer;font-size:15px;color:var(--text-primary);" title="Notifications">🔔
            <span id="hudhud-bell-badge" style="display:none;position:absolute;top:-6px;inset-inline-end:-6px;
                background:#dc2626;color:#fff;border-radius:99px;font-size:10.5px;font-weight:800;
                padding:1px 6px;min-width:18px;text-align:center;">0</span>
        </button>
        <div id="hudhud-bell-dropdown" style="display:none;position:absolute;top:calc(100% + 8px);
            inset-inline-end:0;width:340px;max-height:420px;overflow-y:auto;background:var(--bg-card);
            border:1px solid var(--border-default);border-radius:14px;box-shadow:0 12px 32px rgba(15,23,42,0.14);z-index:90;"></div>
    `;
    actions.appendChild(wrap);

    document.getElementById('hudhud-bell-btn').onclick = toggleBellDropdown;
    document.addEventListener('click', (e) => {
        const dd = document.getElementById('hudhud-bell-dropdown');
        if (dd && !dd.contains(e.target) && e.target.id !== 'hudhud-bell-btn') dd.style.display = 'none';
    });

    refreshNotifications();
    if (!_notifPolling) _notifPolling = setInterval(refreshNotifications, 60000);
}

function getEffectiveLang() {
    return (window.hudhudI18n && window.hudhudI18n.currentLang) ||
           localStorage.getItem('hudhud_lang') ||
           document.documentElement.lang ||
           'en';
}

function localizeNotificationClient(n, lang) {
    if (!n) return n;
    const isEn = lang === 'en';
    const meta = n.meta || {};
    let title = n.title || '';
    let body = n.body || '';

    if (isEn) {
        if (meta.title_en) title = meta.title_en;
        if (meta.body_en) body = meta.body_en;

        // Dynamic Arabic -> English patterns if stored text is Arabic
        if (/أهلاً بك (?:في|إلى) هدهد/i.test(title)) {
            const m = title.match(/أهلاً بك (?:في|إلى) هدهد[،\s]+يا?\s*(.+?)!?$/);
            const name = m ? m[1].trim() : (meta.user_name || '');
            title = name ? `🎉 Welcome to Hudhud, ${name}!` : '🎉 Welcome to Hudhud!';
            body = 'Your account is ready. Next step: connect your social channels from Settings to activate automated replies.';
        } else if (title.includes('تم تفعيل')) {
            const plan = title.replace('✅', '').replace('تم تفعيل', '').replace('خطتك:', '').replace('باقة', '').trim();
            title = plan ? `✅ Plan activated: ${plan}` : '✅ Plan activated';
            if (body.includes('المنصات المشمولة')) {
                const m = body.match(/المنصات المشمولة في خطتك:\s*([^.]+)/);
                const p = m ? m[1].trim() : 'All channels';
                body = `Included platforms: ${p}. AI credits have been updated.`;
            } else if (!meta.body_en) {
                body = 'Your plan is active and AI credits have been added to your balance.';
            }
        } else if (title.includes('بدأت تجربتك المجانية')) {
            title = '✅ Your free trial has started';
            body = 'All messaging channels are available for 3 days.';
        } else if (title.includes('تم إلغاء اشتراكك')) {
            title = '⚠️ Subscription canceled';
            body = 'Channels paused — activate a plan to resume automated service.';
        } else if (title.includes('تم إضافة') && title.includes('رصيد')) {
            const m = title.match(/(\d+)/);
            title = m ? `⚡ Added ${m[1]} AI credits` : '⚡ Added AI credits';
            const tot = body.match(/الآن:\s*(\d+)/);
            body = tot ? `Credits successfully added to your account. Your new total: ${tot[1]} points.` : 'Credits successfully added to your account.';
        } else if (title.includes('رصيد الذكاء الاصطناعي منخفض')) {
            title = '⚠️ Low AI credits warning';
            const m = body.match(/(\d+)/);
            body = m ? `You have ${m[1]} credits remaining. The agent will fall back to static templates when depleted.` : 'Your AI credit balance is running low.';
        } else if (title.includes('رصيد الردود الآلية خلص')) {
            title = '⚠️ Out of AI credits';
            body = 'The AI agent has temporarily paused automated replies because your AI credits are exhausted. New messages will still arrive in your inbox for manual replies.';
        } else if (title.includes('عميل محتمل جديد')) {
            title = '🎯 New qualified lead captured!';
            body = meta.lead_name ? `Your AI agent captured a new prospect: ${meta.lead_name} — view details in your Leads CRM.` : 'Your AI agent captured a new prospect — view details in your Leads CRM.';
        }
    } else {
        if (meta.title_ar) title = meta.title_ar;
        if (meta.body_ar) body = meta.body_ar;
    }

    return Object.assign({}, n, { title, body });
}

async function refreshNotifications() {
    try {
        const lang = getEffectiveLang();
        const res = await fetch(`/api/notifications?limit=20&lang=${encodeURIComponent(lang)}`);
        if (!res.ok) return; // 401 on public pages — silent
        const data = await res.json();
        const badge = document.getElementById('hudhud-bell-badge');
        if (badge) {
            badge.textContent = data.unread || 0;
            badge.style.display = (data.unread || 0) > 0 ? 'block' : 'none';
        }
        renderBellDropdown(data.notifications || []);

        // Toast any new unread notification that hasn't been toasted this session
        try {
            const seen = JSON.parse(sessionStorage.getItem('hudhud_toasted_notifs') || '[]');
            const unread = (data.notifications || []).filter(n => !n.read && !seen.includes(n.id));
            if (unread.length > 0) {
                const latest = unread[0];
                seen.push(latest.id);
                sessionStorage.setItem('hudhud_toasted_notifs', JSON.stringify(seen.slice(-50)));
                const tType = latest.type === 'error' ? 'error' : latest.type === 'warning' ? 'warning' : latest.type === 'success' ? 'success' : 'info';
                const loc = localizeNotificationClient(latest, lang);
                if (window.hudhudToast) {
                    window.hudhudToast.show({
                        title: loc.title,
                        message: loc.body || '',
                        type: tType,
                        duration: 6000
                    });
                }
            }
        } catch (e) {}
    } catch (e) { /* silent — bell is a courtesy */ }
}

function renderBellDropdown(items) {
    const dd = document.getElementById('hudhud-bell-dropdown');
    if (!dd) return;
    const lang = getEffectiveLang();
    const isAr = lang === 'ar';
    if (!items.length) {
        dd.innerHTML = `<div style="padding:24px;text-align:center;color:var(--text-muted);font-size:13px;">${isAr ? 'لا إشعارات بعد' : 'No notifications yet'}</div>`;
        return;
    }
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    const colors = isDark ? {
        success: '#34d399',
        warning: '#fbbf24',
        error: '#f87171',
        broadcast: '#60a5fa',
        info: '#94a3b8'
    } : {
        success: '#059669',
        warning: '#b45309',
        error: '#dc2626',
        broadcast: '#1d4ed8',
        info: '#64748b'
    };
    dd.innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;padding:10px 14px;border-bottom:1px solid var(--border-default);position:sticky;top:0;background:var(--bg-card);">
            <strong style="font-size:13px;">${isAr ? 'الإشعارات' : 'Notifications'}</strong>
            <button onclick="markAllNotificationsRead()" style="background:none;border:none;color:var(--primary);font-size:12px;cursor:pointer;font-weight:600;">${isAr ? 'تعليم الكل كمقروء' : 'Mark all read'}</button>
        </div>
        ${items.map(rawN => {
            const n = localizeNotificationClient(rawN, lang);
            return `
            <div style="padding:11px 14px;border-bottom:1px solid var(--border-default);${n.read ? 'opacity:0.55;' : ''}">
                <div style="font-size:12.8px;font-weight:700;color:${colors[n.type] || 'var(--text-primary)'};">${escapeHtml(n.title)}</div>
                ${n.body ? `<div style="font-size:12px;color:var(--text-secondary);margin-top:2px;">${escapeHtml(n.body)}</div>` : ''}
                <div style="font-size:10.5px;color:var(--text-muted);margin-top:3px;">${escapeHtml(String(n.created_at || '').slice(0, 16).replace('T', ' '))}</div>
            </div>`;
        }).join('')}
    `;
}

function toggleBellDropdown() {
    const dd = document.getElementById('hudhud-bell-dropdown');
    if (dd) dd.style.display = dd.style.display === 'none' ? 'block' : 'none';
}

async function markAllNotificationsRead() {
    try { await fetch('/api/notifications/read-all', { method: 'POST' }); } catch (e) {}
    refreshNotifications();
}

// --------------------------------------------------------------------
// Theme manager (WS-9.4): light | dark | device (follows the user's OS)
// Saved in localStorage; "device" uses prefers-color-scheme automatically.
// --------------------------------------------------------------------
const hudhudTheme = {
    get() {
        const saved = localStorage.getItem('hudhud_theme');
        if (saved === 'dark' || saved === 'light') return saved;
        return 'dark';
    },
    apply() {
        const mode = this.get();
        document.documentElement.setAttribute('data-theme', mode);
        const sel = document.getElementById('hudhud-theme-select');
        if (sel) sel.value = mode;
    },
    set(mode) {
        if (!['light', 'dark'].includes(mode)) return;
        localStorage.setItem('hudhud_theme', mode);
        this.apply();
    },
    injectSwitcher() {
        const topbar = document.querySelector('.app-topbar');
        if (!topbar || document.getElementById('hudhud-theme-select')) return;
        const actions = getOrCreateTopbarActions(topbar);
        const isAr = window.hudhudI18n && window.hudhudI18n.currentLang === 'ar';
        const wrap = document.createElement('div');
        wrap.id = 'hudhud-theme-wrap';
        wrap.style.cssText = 'display:flex;align-items:center;';
        wrap.innerHTML = `
            <select id="hudhud-theme-select" style="background:var(--bg-card);color:var(--text-primary);
                border:1px solid var(--border-default);border-radius:10px;padding:7px 10px;font-family:inherit;
                font-size:12.5px;font-weight:600;cursor:pointer;">
                <option value="light">${isAr ? '☀️ فاتح' : '☀️ Light'}</option>
                <option value="dark">${isAr ? '🌙 داكن' : '🌙 Dark'}</option>
            </select>`;
        const bell = document.getElementById('hudhud-bell');
        if (bell) actions.insertBefore(wrap, bell); else actions.appendChild(wrap);
        wrap.querySelector('select').onchange = (e) => this.set(e.target.value);
        this.apply();
    }
};

// --------------------------------------------------------------------
// Language globe dropdown (WS-9.4) — replaces the simple toggle:
// user opens the globe menu and picks the language explicitly.
// --------------------------------------------------------------------
function injectLanguageGlobe() {
    const topbar = document.querySelector('.app-topbar');
    if (!topbar || document.getElementById('hudhud-lang-globe')) return;
    const actions = getOrCreateTopbarActions(topbar);
    const wrap = document.createElement('div');
    wrap.id = 'hudhud-lang-globe';
    wrap.style.cssText = 'position:relative;display:flex;align-items:center;';
    wrap.innerHTML = `
        <button id="hudhud-lang-btn" style="background:var(--bg-card);color:var(--text-primary);
            border:1px solid var(--border-default);border-radius:10px;padding:7px 12px;cursor:pointer;
            font-size:15px;" title="Language">🌐</button>
        <div id="hudhud-lang-menu" style="display:none;position:absolute;top:calc(100% + 6px);
            inset-inline-start:0;background:var(--bg-card);border:1px solid var(--border-default);
            border-radius:12px;box-shadow:0 10px 26px rgba(15,23,42,0.14);z-index:95;min-width:170px;overflow:hidden;">
            <button onclick="setHudhudLanguage('en')" style="display:flex;gap:8px;align-items:center;width:100%;
                background:none;border:none;padding:10px 14px;cursor:pointer;font-size:13.5px;font-weight:600;
                color:var(--text-primary);">🇺🇸 English</button>
            <button onclick="setHudhudLanguage('ar')" style="display:flex;gap:8px;align-items:center;width:100%;
                background:none;border:none;padding:10px 14px;cursor:pointer;font-size:13.5px;font-weight:600;
                color:var(--text-primary);border-top:1px solid var(--border-default);">🇪🇬 العربية</button>
        </div>`;
    // insert before the theme wrap or bell
    const themeWrap = document.getElementById('hudhud-theme-wrap');
    const bell = document.getElementById('hudhud-bell');
    const anchor = themeWrap || bell;
    if (anchor) actions.insertBefore(wrap, anchor); else actions.appendChild(wrap);
    document.getElementById('hudhud-lang-btn').onclick = (e) => {
        e.stopPropagation();
        const menu = document.getElementById('hudhud-lang-menu');
        if (menu) menu.style.display = menu.style.display === 'none' ? 'block' : 'none';
    };
    document.addEventListener('click', (e) => {
        const menu = document.getElementById('hudhud-lang-menu');
        if (menu && !wrap.contains(e.target)) menu.style.display = 'none';
    });
}

function setHudhudLanguage(lang) {
    if (window.hudhudI18n && window.hudhudI18n.setLanguage) {
        window.hudhudI18n.setLanguage(lang);
    } else {
        localStorage.setItem('hudhud_lang', lang);
        document.cookie = `hudhud_lang=${lang};path=/;max-age=31536000;SameSite=Lax`;
        window.location.reload();
    }
    const menu = document.getElementById('hudhud-lang-menu');
    if (menu) menu.style.display = 'none';
}

document.addEventListener('DOMContentLoaded', () => {
    hudhudRoleManager.init();
    checkSystemMetaStatus();
    // Poll every 60s instead of 15s to avoid burning Meta Graph API rate limits
    setInterval(checkSystemMetaStatus, 60000);
    injectSessionUser();
    injectNotificationsBell();
    hudhudTheme.injectSwitcher();
    injectLanguageGlobe();
});

window.addEventListener('hudhud_lang_change', () => {
    if (lastMetaData) {
        updateMetaStatusBadge(lastMetaData);
    }
    // Re-render role button labels on language change
    const isAr = window.hudhudI18n && window.hudhudI18n.currentLang === 'ar';
    const btnClient = document.querySelector('#hudhud-btn-client span[data-i18n]');
    const btnDev = document.querySelector('#hudhud-btn-dev span[data-i18n]');
    if (btnClient) btnClient.textContent = isAr ? 'واجهة العميل' : 'Client View';
    if (btnDev) btnDev.textContent = isAr ? 'لوحة المطور' : 'Dev Console';
    // Re-render and fetch notifications in the new language
    try { refreshNotifications(); } catch (e) {}
});


// ---- Official platform brand icons (S-B) — from platform registry ----
window.PLATFORM_ICON_SVG = {
    facebook: '<svg viewBox="0 0 24 24" width="100%" height="100%"><path fill="#1877F2" d="M24 12.073C24 5.405 18.627 0 12 0S0 5.405 0 12.073C0 18.1 4.388 23.094 10.125 24v-8.437H7.078v-3.49h3.047v-2.66c0-3.025 1.792-4.697 4.533-4.697 1.313 0 2.686.236 2.686.236v2.971H15.83c-1.491 0-1.956.93-1.956 1.886v2.264h3.328l-.532 3.49h-2.796V24C19.612 23.094 24 18.1 24 12.073z"/></svg>',
    instagram: '<svg viewBox="0 0 24 24" width="100%" height="100%"><defs><radialGradient id="igg__ID__" cx="30%" cy="107%" r="150%"><stop offset="0%" stop-color="#fdf497"/><stop offset="5%" stop-color="#fdf497"/><stop offset="45%" stop-color="#fd5949"/><stop offset="60%" stop-color="#d6249f"/><stop offset="90%" stop-color="#285AEB"/></radialGradient></defs><rect x="1.5" y="1.5" width="21" height="21" rx="5.5" fill="url(#igg__ID__)"/><circle cx="12" cy="12" r="4.7" fill="none" stroke="#fff" stroke-width="1.9"/><circle cx="17.6" cy="6.4" r="1.35" fill="#fff"/></svg>',
    threads: '<svg viewBox="0 0 24 24" width="100%" height="100%"><path fill="#000" d="M17.09 11.33c-.1-.05-.2-.1-.3-.14-.18-3.28-1.95-5.16-4.93-5.18h-.04c-1.78 0-3.26.76-4.17 2.14l1.63 1.12c.68-1.03 1.74-1.25 2.54-1.25h.03c.98.01 1.72.29 2.2.84.35.4.58.95.7 1.64-.87-.15-1.82-.19-2.83-.14-2.85.16-4.68 1.82-4.55 4.13.06 1.17.64 2.18 1.63 2.83.84.55 1.92.82 3.04.76 1.48-.08 2.64-.64 3.45-1.68.62-.78 1.01-1.8 1.18-3.07.71.43 1.24 1 1.53 1.68.5 1.15.53 3.05-1.02 4.6-1.35 1.35-2.98 1.94-5.44 1.96-2.72-.02-4.78-.89-6.11-2.59C3.86 17.4 3.2 15.1 3.18 12c.02-3.1.68-5.4 1.96-6.92 1.33-1.7 3.39-2.57 6.11-2.59 2.74.02 4.84.89 6.24 2.6.68.82 1.19 1.86 1.53 3.06l1.9-.51c-.42-1.53-1.06-2.85-1.96-3.93C17.27 1.63 14.75.54 11.26.51h-.01C7.77.54 5.19 1.63 3.5 3.75 1.98 5.65 1.19 8.36 1.17 11.99v.02c.02 3.63.81 6.34 2.33 8.24 1.69 2.12 4.27 3.21 7.75 3.24h.01c2.99-.02 5.09-.81 6.8-2.52 2.23-2.22 2.16-5 1.43-6.72-.53-1.25-1.54-2.26-2.9-2.92zm-4.9 5.02c-1.25.07-2.55-.49-2.61-1.71-.05-.9.64-1.91 2.7-2.03.24-.01.47-.02.7-.02.75 0 1.45.07 2.09.21-.24 2.94-1.62 3.48-2.88 3.55z"/></svg>',
    whatsapp: '<svg viewBox="0 0 24 24" width="100%" height="100%"><path fill="#25D366" d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413Z"/></svg>',
};

window.platformIcon = function (platform, size = 20) {
    const key = (platform || '').toLowerCase();
    const raw = window.PLATFORM_ICON_SVG[key] ||
        '<svg viewBox="0 0 24 24" width="100%" height="100%"><circle cx="12" cy="12" r="11" fill="#64748b"/><circle cx="12" cy="12" r="4" fill="#fff"/></svg>';
    const svg = raw.replace(/__ID__/g, 'ig' + key + size + Math.floor(Math.random() * 99999));
    return '<span class="platform-brand-icon" style="display:inline-flex;width:' + size +
        'px;height:' + size + 'px;border-radius:6px;overflow:hidden;flex-shrink:0;vertical-align:middle;">' +
        svg + '</span>';
};

// --------------------------------------------------------------------
// Phase 9.6 � toggle-gated product analytics (PostHog), admin-controlled.
// Disabled by default: /api/analytics/config returns {enabled:false} until
// an admin saves analytics_config in site settings. Explicit events only
// (autocapture OFF) + public pageview. window.hudhudTrack(event, props).
// --------------------------------------------------------------------
(function () {
    try {
        fetch('/api/analytics/config').then(function (r) { return r.json(); }).then(function (cfg) {
            if (!cfg || !cfg.enabled || !cfg.posthog_key) return;
            var s = document.createElement('script');
            s.src = 'https://cdn.jsdelivr.net/npm/posthog-js@1.257.0/dist/array.js';
            s.async = true;
            s.onload = function () {
                try {
                    window.posthog = window.posthog || [];
                    window.posthog.init(cfg.posthog_key, {
                        api_host: cfg.posthog_host || 'https://us.i.posthog.com',
                        autocapture: false,
                        capture_pageview: true,
                        capture_performance: true,
                        session_recording: { maskAllInputs: true },
                        persistence: 'localStorage+cookie'
                    });
                    window.hudhudTrack = function (event, props) {
                        try { window.posthog.capture(event, props || {}); } catch (e) { /* noop */ }
                    };
                } catch (e) { /* analytics must never break the app */ }
            };
            document.head.appendChild(s);
        }).catch(function () { /* noop */ });
    } catch (e) { /* noop */ }
})();

// ====================================================================
// Enterprise Hudhud Toast & Notification Engine (Universal Alert System)
// Animated, glassmorphic, theme-aware, RTL/LTR compatible, action-capable
// ====================================================================
const hudhudToast = {
    container: null,
    activeToasts: [],
    maxConcurrent: 4,

    getOrCreateContainer() {
        if (!this.container || !document.body.contains(this.container)) {
            this.container = document.getElementById('hudhud-toast-container');
            if (!this.container) {
                this.container = document.createElement('div');
                this.container.id = 'hudhud-toast-container';
                document.body.appendChild(this.container);
            }
        }
        return this.container;
    },

    getIconSvg(type) {
        switch (type) {
            case 'success':
                return '<svg viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>';
            case 'warning':
                return '<svg viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>';
            case 'error':
                return '<svg viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>';
            case 'info':
            default:
                return '<svg viewBox="0 0 24 24" fill="none" stroke="#3b82f6" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>';
        }
    },

    show(options) {
        if (typeof options === 'string') {
            options = { message: options, type: 'info' };
        }
        const {
            title = '',
            message = '',
            type = 'info',
            duration = 5000,
            actionText = null,
            onAction = null
        } = options;

        const container = this.getOrCreateContainer();

        // Enforce max concurrency limit
        while (this.activeToasts.length >= this.maxConcurrent) {
            const oldest = this.activeToasts.shift();
            if (oldest) this.dismiss(oldest, true);
        }

        const isAr = window.hudhudI18n && window.hudhudI18n.currentLang === 'ar';
        const defaultTitle = title || (
            type === 'success' ? (isAr ? 'تم بنجاح' : 'Success') :
            type === 'error' ? (isAr ? 'حدث خطأ' : 'Error') :
            type === 'warning' ? (isAr ? 'تنبيه' : 'Warning') :
            (isAr ? 'إشعار' : 'Notice')
        );

        const toast = document.createElement('div');
        toast.className = `hudhud-toast toast-${type}`;
        toast.setAttribute('role', 'alert');

        let actionHtml = '';
        if (actionText && typeof onAction === 'function') {
            actionHtml = `<div class="hudhud-toast-actions"><button type="button" class="hudhud-toast-btn hudhud-toast-btn-primary">${escapeHtml(actionText)}</button></div>`;
        }

        toast.innerHTML = `
            <div class="hudhud-toast-main">
                <div class="hudhud-toast-icon">${this.getIconSvg(type)}</div>
                <div class="hudhud-toast-body">
                    <div class="hudhud-toast-title">${escapeHtml(defaultTitle)}</div>
                    <div class="hudhud-toast-message">${escapeHtml(message)}</div>
                    ${actionHtml}
                </div>
                <button type="button" class="hudhud-toast-close" title="${isAr ? 'إغلاق' : 'Dismiss'}">✕</button>
            </div>
            ${duration > 0 ? '<div class="hudhud-toast-progress"><div class="hudhud-toast-progress-bar"></div></div>' : ''}
        `;

        if (actionText && typeof onAction === 'function') {
            const btn = toast.querySelector('.hudhud-toast-btn');
            if (btn) {
                btn.onclick = (e) => {
                    e.stopPropagation();
                    try { onAction(); } catch (err) { console.error(err); }
                    this.dismiss(toast);
                };
            }
        }

        const closeBtn = toast.querySelector('.hudhud-toast-close');
        if (closeBtn) {
            closeBtn.onclick = (e) => {
                e.stopPropagation();
                this.dismiss(toast);
            };
        }

        container.appendChild(toast);
        this.activeToasts.push(toast);

        // Auto-dismiss with progress countdown and pause on hover
        if (duration > 0) {
            const progressBar = toast.querySelector('.hudhud-toast-progress-bar');
            let remaining = duration;
            let startTime = Date.now();
            let timer = null;

            const startTimer = () => {
                startTime = Date.now();
                if (progressBar) {
                    progressBar.style.transition = `width ${remaining}ms linear`;
                    progressBar.style.width = '0%';
                }
                timer = setTimeout(() => {
                    this.dismiss(toast);
                }, remaining);
            };

            const pauseTimer = () => {
                clearTimeout(timer);
                const elapsed = Date.now() - startTime;
                remaining = Math.max(0, remaining - elapsed);
                if (progressBar) {
                    const currentPct = (remaining / duration) * 100;
                    progressBar.style.transition = 'none';
                    progressBar.style.width = `${currentPct}%`;
                }
            };

            toast.onmouseenter = pauseTimer;
            toast.onmouseleave = startTimer;
            startTimer();
        }

        return toast;
    },

    dismiss(toast, immediate = false) {
        if (!toast || !toast.parentNode) return;
        const idx = this.activeToasts.indexOf(toast);
        if (idx !== -1) this.activeToasts.splice(idx, 1);

        if (immediate) {
            toast.remove();
        } else {
            toast.classList.add('toast-hiding');
            setTimeout(() => {
                try { toast.remove(); } catch (e) {}
            }, 250);
        }
    },

    success(message, title = '', options = {}) {
        return this.show({ message, title, type: 'success', ...options });
    },

    error(message, title = '', options = {}) {
        return this.show({ message, title, type: 'error', ...options });
    },

    warning(message, title = '', options = {}) {
        return this.show({ message, title, type: 'warning', ...options });
    },

    info(message, title = '', options = {}) {
        return this.show({ message, title, type: 'info', ...options });
    }
};

window.hudhudToast = hudhudToast;
window.toast = hudhudToast;

// Polite non-blocking replacement for window.alert
window.alert = function (message) {
    if (typeof message === 'object') {
        try { message = JSON.stringify(message); } catch (e) {}
    }
    const str = String(message || '');
    if (str.toLowerCase().includes('fail') || str.toLowerCase().includes('error') || str.includes('خطأ') || str.includes('فشل')) {
        hudhudToast.error(str);
    } else if (str.toLowerCase().includes('success') || str.includes('نجاح') || str.includes('✓') || str.includes('✅')) {
        hudhudToast.success(str);
    } else if (str.toLowerCase().includes('warn') || str.includes('تنبيه') || str.includes('تحذير') || str.includes('⚠️')) {
        hudhudToast.warning(str);
    } else {
        hudhudToast.info(str);
    }
};

// Global fetch observer for automatic error/credit handling
(function() {
    const originalFetch = window.fetch;
    window.fetch = async function(...args) {
        try {
            const response = await originalFetch.apply(this, args);
            // 402: Insufficient credits
            if (response.status === 402) {
                const url = typeof args[0] === 'string' ? args[0] : (args[0] && args[0].url) || '';
                // Don't toast if it's a silent auth check
                if (!url.includes('/auth/me')) {
                    const isAr = window.hudhudI18n && window.hudhudI18n.currentLang === 'ar';
                    hudhudToast.warning(
                        isAr ? 'رصيدك غير كافٍ لإتمام هذه العملية. يرجى تجديد الاشتراك أو شحن الرصيد.' 
                             : 'Insufficient AI credits. Please recharge or renew your subscription.',
                        isAr ? 'رصيد الذكاء الاصطناعي نافد' : 'AI Credits Depleted',
                        {
                            duration: 7000,
                            actionText: isAr ? 'شحن الرصيد' : 'Top Up / Upgrade',
                            onAction: () => { window.location.href = '/onboarding'; }
                        }
                    );
                }
            }
            return response;
        } catch (err) {
            throw err;
        }
    };
})();


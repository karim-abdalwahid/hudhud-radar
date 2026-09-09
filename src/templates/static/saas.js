// HudhudRadar / Hudhud — Unified SaaS Common Client JS
// Provides: System Health Polling, Meta Status, and Client vs Developer Role Separation

let lastMetaData = null;

const hudhudRoleManager = {
    DEV_ROUTES: ['/settings', '/identity', '/analytics'],

    getMode() {
        // If current URL is a developer route, default to developer mode
        const currentPath = window.location.pathname;
        const isDevRoute = this.DEV_ROUTES.some(r => currentPath.startsWith(r));
        const saved = localStorage.getItem('hudhud_role_mode');
        if (saved) return saved;
        return isDevRoute ? 'developer' : 'client';
    },

    setMode(mode) {
        localStorage.setItem('hudhud_role_mode', mode);
        this.applyMode(mode);

        const currentPath = window.location.pathname;
        const isDevRoute = this.DEV_ROUTES.some(r => currentPath.startsWith(r));

        if (mode === 'client' && isDevRoute) {
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

    injectRoleSwitcher() {
        this.normalizeBrandLogo();
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

        // Group developer navigation items
        this.organizeDevNav(sidebar, isAr);

        // NOTE (WS0.4): sidebar nav links are now rendered SERVER-SIDE from the
        // module registry — the old client-side Automations injection is gone.

        // Add developer console banner if currently on a dev route
        this.injectDevPageBanner();
    },

    organizeDevNav(sidebar, isAr) {
        const nav = sidebar.querySelector('.sidebar-nav');
        if (!nav) return;

        // If dev-nav-section already exists, return
        if (nav.querySelector('.dev-nav-section')) return;

        // Find links for /identity, /analytics, /settings
        const devLinks = Array.from(nav.querySelectorAll('a.nav-item')).filter(a => {
            const href = a.getAttribute('href') || '';
            return href.includes('/identity') || href.includes('/analytics') || href.includes('/settings');
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
    },

    init() {
        const mode = this.getMode();
        this.applyMode(mode);
        this.injectRoleSwitcher();
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
        const chip = document.createElement('div');
        chip.id = 'hudhud-user-chip';
        chip.style.cssText = 'display:flex;align-items:center;gap:8px;padding:10px 12px;margin-top:8px;border-top:1px solid var(--border-default);';
        chip.innerHTML = `
            <div style="min-width:0;flex:1;">
                <div style="font-size:12px;font-weight:600;color:var(--text-primary);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${escapeHtml(me.email || '')}</div>
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

function injectNotificationsBell() {
    // Only dashboard pages (topbar exists there); skip landing/auth
    const topbar = document.querySelector('.app-topbar');
    if (!topbar || document.getElementById('hudhud-bell')) return;

    const wrap = document.createElement('div');
    wrap.id = 'hudhud-bell';
    wrap.style.cssText = 'position:relative;margin-inline-start:auto;display:flex;align-items:center;gap:10px;';
    wrap.innerHTML = `
        <button id="hudhud-bell-btn" style="position:relative;background:none;border:1px solid var(--border-default);
            border-radius:12px;padding:8px 11px;cursor:pointer;font-size:16px;" title="Notifications">🔔
            <span id="hudhud-bell-badge" style="display:none;position:absolute;top:-6px;inset-inline-end:-6px;
                background:#dc2626;color:#fff;border-radius:99px;font-size:10.5px;font-weight:800;
                padding:1px 6px;min-width:18px;text-align:center;">0</span>
        </button>
        <div id="hudhud-bell-dropdown" style="display:none;position:absolute;top:calc(100% + 8px);
            inset-inline-end:0;width:340px;max-height:420px;overflow-y:auto;background:var(--bg-card);
            border:1px solid var(--border-default);border-radius:14px;box-shadow:0 12px 32px rgba(15,23,42,0.14);z-index:90;"></div>
    `;
    topbar.appendChild(wrap);

    document.getElementById('hudhud-bell-btn').onclick = toggleBellDropdown;
    document.addEventListener('click', (e) => {
        const dd = document.getElementById('hudhud-bell-dropdown');
        if (dd && !dd.contains(e.target) && e.target.id !== 'hudhud-bell-btn') dd.style.display = 'none';
    });

    refreshNotifications();
    if (!_notifPolling) _notifPolling = setInterval(refreshNotifications, 60000);
}

async function refreshNotifications() {
    try {
        const res = await fetch('/api/notifications?limit=20');
        if (!res.ok) return; // 401 on public pages — silent
        const data = await res.json();
        const badge = document.getElementById('hudhud-bell-badge');
        if (badge) {
            badge.textContent = data.unread || 0;
            badge.style.display = (data.unread || 0) > 0 ? 'block' : 'none';
        }
        renderBellDropdown(data.notifications || []);
    } catch (e) { /* silent — bell is a courtesy */ }
}

function renderBellDropdown(items) {
    const dd = document.getElementById('hudhud-bell-dropdown');
    if (!dd) return;
    const isAr = window.hudhudI18n && window.hudhudI18n.currentLang === 'ar';
    if (!items.length) {
        dd.innerHTML = `<div style="padding:24px;text-align:center;color:var(--text-muted);font-size:13px;">${isAr ? 'لا إشعارات بعد' : 'No notifications yet'}</div>`;
        return;
    }
    const colors = { success: '#059669', warning: '#b45309', error: '#dc2626', broadcast: '#1d4ed8', info: '#64748b' };
    dd.innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;padding:10px 14px;border-bottom:1px solid var(--border-default);position:sticky;top:0;background:var(--bg-card);">
            <strong style="font-size:13px;">${isAr ? 'الإشعارات' : 'Notifications'}</strong>
            <button onclick="markAllNotificationsRead()" style="background:none;border:none;color:var(--primary);font-size:12px;cursor:pointer;font-weight:600;">${isAr ? 'تعليم الكل كمقروء' : 'Mark all read'}</button>
        </div>
        ${items.map(n => `
            <div style="padding:11px 14px;border-bottom:1px solid var(--border-default);${n.read ? 'opacity:0.55;' : ''}">
                <div style="font-size:12.8px;font-weight:700;color:${colors[n.type] || 'var(--text-primary)'};">${escapeHtml(n.title)}</div>
                ${n.body ? `<div style="font-size:12px;color:var(--text-secondary);margin-top:2px;">${escapeHtml(n.body)}</div>` : ''}
                <div style="font-size:10.5px;color:var(--text-muted);margin-top:3px;">${escapeHtml(String(n.created_at || '').slice(0, 16).replace('T', ' '))}</div>
            </div>`).join('')}
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
        const saved = localStorage.getItem('hudhud_theme') || 'device';
        if (saved === 'dark' || saved === 'light') return saved;
        // device mode
        return (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches)
            ? 'dark' : 'light';
    },
    apply() {
        const mode = localStorage.getItem('hudhud_theme') || 'device';
        const effective = this.get();
        document.documentElement.setAttribute('data-theme', effective);
        const sel = document.getElementById('hudhud-theme-select');
        if (sel) sel.value = mode;
    },
    set(mode) {
        if (!['light', 'dark', 'device'].includes(mode)) return;
        localStorage.setItem('hudhud_theme', mode);
        this.apply();
    },
    injectSwitcher() {
        const topbar = document.querySelector('.app-topbar');
        if (!topbar || document.getElementById('hudhud-theme-select')) return;
        const isAr = window.hudhudI18n && window.hudhudI18n.currentLang === 'ar';
        const wrap = document.createElement('div');
        wrap.style.cssText = 'display:flex;align-items:center;margin-inline-start:auto;gap:8px;';
        wrap.innerHTML = `
            <select id="hudhud-theme-select" style="background:var(--bg-card);color:var(--text-primary);
                border:1px solid var(--border-default);border-radius:10px;padding:7px 10px;font-family:inherit;
                font-size:12.5px;font-weight:600;cursor:pointer;">
                <option value="light">${isAr ? '☀️ فاتح' : '☀️ Light'}</option>
                <option value="dark">${isAr ? '🌙 داكن' : '🌙 Dark'}</option>
                <option value="device">${isAr ? '🖥️ حسب الجهاز' : '🖥️ Device'}</option>
            </select>`;
        // Bell is appended after — keep bell last (right side)
        const bell = document.getElementById('hudhud-bell');
        if (bell) topbar.insertBefore(wrap, bell); else topbar.appendChild(wrap);
        wrap.querySelector('select').onchange = (e) => this.set(e.target.value);
        this.apply();
        // follow OS live in device mode
        if (window.matchMedia) {
            window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
                if ((localStorage.getItem('hudhud_theme') || 'device') === 'device') this.apply();
            });
        }
    }
};

// --------------------------------------------------------------------
// Language globe dropdown (WS-9.4) — replaces the simple toggle:
// user opens the globe menu and picks the language explicitly.
// --------------------------------------------------------------------
function injectLanguageGlobe() {
    const topbar = document.querySelector('.app-topbar');
    if (!topbar || document.getElementById('hudhud-lang-globe')) return;
    const isAr = window.hudhudI18n && window.hudhudI18n.currentLang === 'ar';
    const wrap = document.createElement('div');
    wrap.id = 'hudhud-lang-globe';
    wrap.style.cssText = 'position:relative;display:flex;align-items:center;gap:8px;';
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
    // insert before the theme select
    const themeSel = document.getElementById('hudhud-theme-select');
    const anchor = themeSel ? themeSel.parentElement : null;
    if (anchor) topbar.insertBefore(wrap, anchor); else topbar.appendChild(wrap);
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
});

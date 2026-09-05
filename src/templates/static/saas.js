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

        // Ensure Automations navigation link is present in Workspaces
        const nav = sidebar.querySelector('.sidebar-nav');
        if (nav) {
            const studioLink = nav.querySelector('a[href="/studio"]');
            if (studioLink && !nav.querySelector('a[href="/automations"]')) {
                const autoLink = document.createElement('a');
                autoLink.href = '/automations';
                autoLink.className = `nav-item ${window.location.pathname === '/automations' ? 'active' : ''}`;
                autoLink.innerHTML = `<span class="nav-icon">⚡</span> <span data-i18n="nav.automations">${isAr ? 'الأتمتة وسير العمل' : 'Automations'}</span>`;
                studioLink.insertAdjacentElement('afterend', autoLink);
            }
        }

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

document.addEventListener('DOMContentLoaded', () => {
    hudhudRoleManager.init();
    checkSystemMetaStatus();
    setInterval(checkSystemMetaStatus, 15000);
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

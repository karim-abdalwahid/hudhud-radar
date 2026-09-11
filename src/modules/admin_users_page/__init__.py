"""
Admin Users management page (WS-E+H) — /users.

Admin-only via pages module access declaration + middleware. Uses the
shared dashboard chrome (render_page_template handles sidebar/i18n/base).
"""
from fastapi import FastAPI, Request

from src.core.modules import module_registry, NavEntry, PageSpec, ACCESS_ADMIN

_ADMIN_USERS_HTML = """<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Admin — Users & Console</title>
<link rel="icon" href="/static/favicon.ico" sizes="any">
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Tajawal:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/static/saas.css">
<style>
/* Page-only styles — the shared chrome (layout/sidebar/topbar/panels/badges/
   buttons/chips/modal) comes from saas.css, same as every other page. */
.search{width:280px;padding:9px 14px;border:1px solid var(--border-default);border-radius:10px;font-family:inherit;font-size:13px;}
td .btn{white-space:nowrap;}
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
                <span class="crumb-current">Admin Console — Users & Site</span>
            </div>
            <div class="topbar-actions" style="display:flex; gap:10px; align-items:center;">
                <button type="button" class="lang-switcher-btn" onclick="window.hudhudI18n.toggle()">
                    <span data-i18n="lang.switch_btn">🌐 العربية</span>
                </button>
            </div>
        </header>

        <div class="app-content">
            <div class="metrics-strip" id="kpi-strip">
                <div class="metric-card"><div class="metric-label">Total Users</div><div class="metric-val" id="kpi-users">—</div></div>
                <div class="metric-card"><div class="metric-label">Signups (7d)</div><div class="metric-val" id="kpi-signups">—</div></div>
                <div class="metric-card"><div class="metric-label">Page Views (7d)</div><div class="metric-val" id="kpi-views">—</div></div>
                <div class="metric-card"><div class="metric-label">Leads</div><div class="metric-val" id="kpi-leads">—</div></div>
                <div class="metric-card"><div class="metric-label">AI Calls</div><div class="metric-val" id="kpi-ai">—</div></div>
            </div>

            <div class="panel-section">
                <div class="panel-header"><div><h3 class="panel-title">Plans Distribution</h3>
                <div class="panel-desc">Subscriptions across the workspace</div></div></div>
                <div id="plans-dist" style="font-size:13px;color:var(--text-secondary);">—</div>
            </div>

            <div class="panel-section">
                <div class="panel-header"><div><h3 class="panel-title">Users Management</h3>
                <div class="panel-desc">Accounts, roles, plans, credits and access</div></div></div>
                <div style="display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:14px;">
                    <input class="search" id="searchBox" placeholder="Search by email or name…" oninput="usersView.apply()">
                    <div id="role-chips" style="display:flex;gap:6px;">
                        <button type="button" class="chip active" data-role="all" onclick="usersView.setRole('all')">All</button>
                        <button type="button" class="chip" data-role="admin" onclick="usersView.setRole('admin')">Admins</button>
                        <button type="button" class="chip" data-role="user" onclick="usersView.setRole('user')">Users</button>
                    </div>
                    <select id="status-filter" onchange="usersView.apply()" style="padding:8px 12px;border:1px solid var(--border-default);border-radius:10px;font-family:inherit;font-size:13px;">
                        <option value="all">Any status</option>
                        <option value="active">Active only</option>
                        <option value="disabled">Disabled only</option>
                    </select>
                </div>
                <div style="overflow-x:auto;">
                <table>
                    <thead><tr>
                        <th>User</th>
                        <th>Role</th>
                        <th>Status</th>
                        <th>Plan</th>
                        <th class="sortable" onclick="usersView.setSort('ai_credits')">AI Credits <span id="sort-ai_credits"></span></th>
                        <th class="sortable" onclick="usersView.setSort('leads_count')">Leads <span id="sort-leads_count"></span></th>
                        <th class="sortable" onclick="usersView.setSort('created_at')">Joined <span id="sort-created_at"></span></th>
                        <th>Actions</th>
                    </tr></thead>
                    <tbody id="users-body"><tr><td colspan="8" style="text-align:center;color:var(--text-muted);padding:24px;">Loading…</td></tr></tbody>
                </table>
                </div>
                <div id="pager" style="display:flex;gap:8px;align-items:center;justify-content:flex-end;margin-top:12px;font-size:12.5px;color:var(--text-secondary);"></div>
            </div>

            <div class="panel-section">
                <div class="panel-header"><div><h3 class="panel-title">Traffic — Top Paths</h3>
                <div class="panel-desc">Internal dashboard traffic log (7 days)</div></div></div>
                <div id="traffic-box"><div style="color:var(--text-muted);font-size:13px;">Loading…</div></div>
            </div>

            <div class="panel-section">
                <div class="panel-header"><div><h3 class="panel-title">Product Analytics (PostHog)</h3>
                <div class="panel-desc">Toggle-gated — disabled means zero tracking (privacy-safe default)</div></div></div>
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;flex-wrap:wrap;">
                    <label style="display:flex;align-items:center;gap:6px;font-size:13px;font-weight:700;">
                        <input type="checkbox" id="ph-enabled"> Enabled
                    </label>
                </div>
                <div style="display:grid;gap:10px;max-width:560px;">
                    <div>
                        <label style="font-size:11.5px;color:var(--text-muted);font-weight:600;text-transform:uppercase;">Project API Key</label>
                        <input id="ph-key" placeholder="phc_..." style="width:100%;padding:9px 12px;border:1px solid var(--border-default);border-radius:10px;font-family:inherit;font-size:13px;margin-top:4px;">
                    </div>
                    <div>
                        <label style="font-size:11.5px;color:var(--text-muted);font-weight:600;text-transform:uppercase;">Host (EU: https://eu.i.posthog.com)</label>
                        <input id="ph-host" value="https://eu.i.posthog.com" style="width:100%;padding:9px 12px;border:1px solid var(--border-default);border-radius:10px;font-family:inherit;font-size:13px;margin-top:4px;">
                    </div>
                    <div><button class="btn-primary" style="padding:9px 18px;" onclick="saveAnalytics()">💾 Save analytics config</button>
                    <span id="ph-status" style="font-size:12.5px;margin-inline-start:10px;"></span></div>
                </div>
            </div>
        </div>
    </main>
</div>
<script src="/static/i18n.js"></script>
<script src="/static/saas.js"></script>
<script>
async function loadOverview() {
    try {
        const r = await fetch('/api/admin/overview');
        const d = await r.json();
        document.getElementById('kpi-users').textContent = d.users_total;
        document.getElementById('kpi-signups').textContent = d.signups_7d;
        document.getElementById('kpi-views').textContent = d.traffic_views_7d;
        document.getElementById('kpi-leads').textContent = d.leads_total;
        document.getElementById('kpi-ai').textContent = d.ai_calls;
        document.getElementById('plans-dist').textContent = Object.entries(d.plan_distribution)
            .map(([p, c]) => `${p}: ${c}`).join('  ·  ') || 'no users yet';
    } catch (e) { console.error(e); }
}

// ------------------------------------------------------------------
// Users view: load once, then filter/sort/paginate client-side.
// Replaces per-keystroke API calls + native prompt()/confirm() dialogs.
// ------------------------------------------------------------------
const usersView = {
    all: [],
    role: 'all',
    sortKey: 'created_at',
    sortDir: -1,          // -1 = newest/highest first
    page: 1,
    pageSize: 10,

    async load() {
        const body = document.getElementById('users-body');
        try {
            const r = await fetch('/api/admin/users?search=');
            const d = await r.json();
            this.all = d.users || [];
            this.page = 1;
            this.render();
        } catch (e) {
            body.innerHTML = '<tr><td colspan="8" style="text-align:center;color:#dc2626;padding:24px;">Failed to load users</td></tr>';
        }
    },

    setRole(role) {
        this.role = role;
        document.querySelectorAll('#role-chips .chip').forEach(c => c.classList.toggle('active', c.dataset.role === role));
        this.page = 1;
        this.render();
    },

    setSort(key) {
        if (this.sortKey === key) { this.sortDir = -this.sortDir; }
        else { this.sortKey = key; this.sortDir = -1; }
        document.querySelectorAll('th.sortable span').forEach(s => s.textContent = '');
        const arrow = document.getElementById('sort-' + key);
        if (arrow) arrow.textContent = this.sortDir === -1 ? '▾' : '▴';
        this.render();
    },

    filtered() {
        const q = (document.getElementById('searchBox').value || '').trim().toLowerCase();
        const status = document.getElementById('status-filter').value;
        return this.all.filter(u => {
            if (this.role !== 'all' && u.role !== this.role) return false;
            if (status === 'active' && !u.is_active) return false;
            if (status === 'disabled' && u.is_active) return false;
            if (q && !((u.email || '') + ' ' + (u.full_name || '')).toLowerCase().includes(q)) return false;
            return true;
        }).sort((a, b) => {
            const va = a[this.sortKey] ?? '';
            const vb = b[this.sortKey] ?? '';
            if (typeof va === 'number' && typeof vb === 'number') return (va - vb) * -this.sortDir;
            return String(va).localeCompare(String(vb)) * -this.sortDir;
        });
    },

    render() {
        const rows = this.filtered();
        const body = document.getElementById('users-body');
        const pages = Math.max(1, Math.ceil(rows.length / this.pageSize));
        if (this.page > pages) this.page = pages;

        if (!rows.length) {
            body.innerHTML = '<tr><td colspan="8" style="text-align:center;color:var(--text-muted);padding:24px;">No users match the filters</td></tr>';
        } else {
            const slice = rows.slice((this.page - 1) * this.pageSize, this.page * this.pageSize);
            body.innerHTML = slice.map(u => `
                <tr>
                    <td><strong>${escapeHtml(u.email)}</strong><br><span style="color:var(--text-muted);font-size:11.5px;">${escapeHtml(u.full_name || '')}</span></td>
                    <td>${u.role === 'admin' ? '<span class="badge badge-plan">ADMIN</span>' : 'user'}</td>
                    <td><span class="badge ${u.is_active ? 'badge-ok' : 'badge-off'}">${u.is_active ? 'Active' : 'Disabled'}</span></td>
                    <td><span class="badge badge-plan">${escapeHtml(u.plan || 'free')}</span></td>
                    <td id="credits-${u.id}">${u.ai_credits}</td>
                    <td>${u.leads_count}</td>
                    <td style="font-size:11.5px;color:var(--text-muted);">${String(u.created_at || '').slice(0, 10)}</td>
                    <td>
                        <button class="btn btn-ghost" onclick="openCreditsModal('${u.id}')">+ Credits</button>
                        <button class="btn btn-ghost" onclick="cyclePlan('${u.id}', '${u.plan || 'free'}')">Plan ▸</button>
                        ${u.role !== 'admin' ? `<button class="btn ${u.is_active ? 'btn-danger' : 'btn-primary'}" onclick="toggleActive('${u.id}', ${u.is_active})">${u.is_active ? 'Disable' : 'Enable'}</button>` : ''}
                    </td>
                </tr>`).join('');
        }

        const pager = document.getElementById('pager');
        pager.innerHTML = `
            <span>${rows.length} user(s) · page ${this.page}/${pages}</span>
            <button class="btn btn-ghost" ${this.page <= 1 ? 'disabled' : ''} onclick="usersView.goto(${this.page - 1})">‹ Prev</button>
            <button class="btn btn-ghost" ${this.page >= pages ? 'disabled' : ''} onclick="usersView.goto(${this.page + 1})">Next ›</button>`;
    },

    goto(p) { this.page = p; this.render(); },

    refresh() { this.load(); }
};

function loadUsers(search = '') { usersView.load(); }

// ------------------------------------------------------------------
// Proper modals (replace native prompt()/confirm())
// ------------------------------------------------------------------
function openModal(title, bodyHtml, confirmLabel, onConfirm) {
    let back = document.getElementById('app-modal');
    if (!back) {
        back = document.createElement('div');
        back.id = 'app-modal';
        back.className = 'modal-backdrop';
        document.body.appendChild(back);
    }
    back.innerHTML = `
        <div class="modal">
            <h4>${escapeHtml(title)}</h4>
            ${bodyHtml}
            <div class="err" id="modal-err"></div>
            <div class="modal-actions">
                <button class="btn btn-ghost" onclick="closeModal()">Cancel</button>
                <button class="btn btn-primary" id="modal-confirm">${escapeHtml(confirmLabel)}</button>
            </div>
        </div>`;
    back.style.display = 'flex';
    back.onclick = (e) => { if (e.target === back) closeModal(); };
    document.getElementById('modal-confirm').onclick = async () => {
        const err = await onConfirm();
        if (err) document.getElementById('modal-err').textContent = err;
        else closeModal();
    };
}

function closeModal() {
    const back = document.getElementById('app-modal');
    if (back) back.style.display = 'none';
}

function openCreditsModal(userId) {
    openModal('Grant AI Credits', `
        <p>Enter the number of AI credits to grant this user.</p>
        <input id="credits-amount" type="number" min="1" step="1" value="100">`,
        'Grant', async () => {
            const amount = parseInt(document.getElementById('credits-amount').value, 10);
            if (!amount || amount <= 0) return 'Enter a positive whole number.';
            const r = await fetch(`/api/admin/users/${userId}/credits`, {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ amount })
            });
            const d = await r.json();
            if (d.status === 'success') {
                const cell = document.getElementById('credits-' + userId);
                if (cell) cell.textContent = d.ai_credits;
                return null;
            }
            return d.detail || 'Failed to grant credits.';
        });
}

const PLAN_CYCLE = { 'free': 'starter', 'starter': 'growth', 'growth': 'scale', 'scale': 'free' };
async function cyclePlan(userId, current) {
    const next = PLAN_CYCLE[current] || 'free';
    openModal('Change Plan', `<p>Set this user's plan to <strong>"${escapeHtml(next)}"</strong>?`, 'Change Plan', async () => {
        const r = await fetch(`/api/admin/users/${userId}/plan`, {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ plan: next })
        });
        if (r.ok) { usersView.load(); return null; }
        const d = await r.json().catch(() => ({}));
        return d.detail || 'Failed to set plan';
    });
}

async function toggleActive(userId, currentActive) {
    openModal(
        currentActive ? 'Disable User' : 'Enable User',
        currentActive
            ? '<p>This user will <strong>not be able to sign in</strong> until re-enabled. Continue?</p>'
            : '<p>Re-enable sign-in for this user?</p>',
        currentActive ? 'Disable' : 'Enable',
        async () => {
            const r = await fetch(`/api/admin/users/${userId}`, {
                method: 'PATCH', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ is_active: !currentActive })
            });
            if (r.ok) { usersView.load(); return null; }
            const d = await r.json().catch(() => ({}));
            return d.detail || 'Failed';
        });
}

async function loadTraffic() {
    try {
        const r = await fetch('/api/admin/traffic');
        const d = await r.json();
        const box = document.getElementById('traffic-box');
        const entries = Object.entries(d.by_path || {});
        if (!entries.length) { box.innerHTML = '<div style="color:var(--text-muted);font-size:13px;">No traffic recorded yet</div>'; return; }
        box.innerHTML = entries.map(([p, c]) => `<div class="traffic-row"><span>${escapeHtml(p)}</span><strong>${c}</strong></div>`).join('');
    } catch (e) { console.error(e); }
}

// Phase 9.6 — PostHog toggle-gated config (site-settings: analytics_config)
async function loadAnalytics() {
    try {
        const r = await fetch('/api/admin/site-settings');
        const d = await r.json();
        const cfg = (d.settings || {}).analytics_config || {};
        document.getElementById('ph-enabled').checked = !!cfg.enabled;
        document.getElementById('ph-key').value = cfg.posthog_key || '';
        document.getElementById('ph-host').value = cfg.posthog_host || 'https://eu.i.posthog.com';
    } catch (e) { console.error(e); }
}

async function saveAnalytics() {
    const status = document.getElementById('ph-status');
    const cfg = {
        enabled: document.getElementById('ph-enabled').checked,
        posthog_key: document.getElementById('ph-key').value.trim(),
        posthog_host: document.getElementById('ph-host').value.trim() || 'https://eu.i.posthog.com'
    };
    const r = await fetch('/api/admin/site-settings', {
        method: 'PUT', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ analytics_config: cfg })
    });
    if (r.ok) { status.textContent = '✅ Saved'; status.style.color = '#059669'; }
    else { const d = await r.json().catch(() => ({})); status.textContent = '❌ ' + (d.detail || 'Failed'); status.style.color = '#dc2626'; }
    setTimeout(() => { status.textContent = ''; }, 3000);
}

document.addEventListener('DOMContentLoaded', () => { loadOverview(); loadUsers(); loadTraffic(); loadAnalytics(); });
</script>
</body>
</html>"""


def register(app: FastAPI) -> None:
    @app.get("/users", include_in_schema=False)
    async def admin_users_page(request: Request):
        from src.modules.pages import render_module_page
        return render_module_page(_ADMIN_USERS_HTML, request)


module_registry.register_module(
    name="admin_users_page",
    description="/users admin dashboard page (users mgmt, KPIs, traffic, AI usage)",
    register_router=register,
    pages=[PageSpec(path="/users", template="admin_users", access=ACCESS_ADMIN)],
    nav=[
        NavEntry(href="/users", label_key="nav.users_admin", icon="🎛️",
                 section="nav.analytics_system", order=3, admin_only=True),
    ],
)

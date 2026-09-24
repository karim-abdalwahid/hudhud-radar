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

/* Plans Distribution Grid */
.plans-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 12px;
    margin-top: 10px;
}
.plan-card {
    background: var(--bg-card);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-sm);
    padding: 14px 16px;
    display: flex;
    flex-direction: column;
    gap: 10px;
    transition: all var(--transition-fast);
}
.plan-card:hover {
    border-color: var(--border-hover);
    transform: translateY(-2px);
    box-shadow: var(--shadow-sm);
}
.plan-card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.plan-name-wrap {
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: 700;
    font-size: 14px;
    color: var(--text-primary);
    text-transform: capitalize;
}
.plan-badge {
    font-size: 11.5px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 99px;
}
.plan-count-row {
    display: flex;
    align-items: baseline;
    gap: 6px;
}
.plan-count {
    font-size: 24px;
    font-weight: 800;
    color: var(--text-primary);
    line-height: 1;
}
.plan-sub {
    font-size: 12px;
    color: var(--text-muted);
}
.plan-progress-track {
    width: 100%;
    height: 6px;
    background: var(--bg-subtle);
    border-radius: 99px;
    overflow: hidden;
}
.plan-progress-fill {
    height: 100%;
    border-radius: 99px;
    transition: width 0.4s ease;
}

/* Users Management Table Alignment & Polish */
.users-table-wrap {
    overflow-x: auto;
    border: 1px solid var(--border-default);
    border-radius: var(--radius-sm) var(--radius-sm) 0 0;
    background: var(--bg-card);
}
.users-table {
    width: 100%;
    border-collapse: collapse;
    text-align: start;
    table-layout: auto;
}
.users-table th {
    text-align: start;
    padding: 12px 16px;
    font-size: 11.5px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-muted);
    background: var(--bg-subtle);
    border-bottom: 1px solid var(--border-default);
    white-space: nowrap;
    vertical-align: middle;
}
.users-table th.sortable {
    cursor: pointer;
    user-select: none;
}
.users-table th.sortable:hover {
    color: var(--text-primary);
}
.users-table th.th-actions {
    text-align: end;
}
.users-table td {
    text-align: start;
    padding: 13px 16px;
    font-size: 13px;
    color: var(--text-primary);
    border-bottom: 1px solid var(--border-subtle);
    vertical-align: middle;
}
.users-table td.td-actions {
    text-align: end;
    white-space: nowrap;
}
.users-table tr:hover td {
    background: var(--bg-hover);
}
.users-table .actions-wrap {
    display: inline-flex;
    gap: 6px;
    justify-content: flex-end;
    align-items: center;
}

.pagination-wrap {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 18px;
    background: var(--bg-card);
    border: 1px solid var(--border-default);
    border-top: none;
    border-radius: 0 0 var(--radius-sm) var(--radius-sm);
    margin-top: 0;
    font-size: 13px;
    color: var(--text-secondary);
    flex-wrap: wrap;
    gap: 10px;
}
.pagination-btns {
    display: flex;
    gap: 8px;
    align-items: center;
}
.traffic-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-top: 12px;
}
.traffic-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 14px;
    background: var(--bg-input);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-sm);
    gap: 14px;
    transition: all var(--transition-fast);
}
.traffic-item:hover {
    background: var(--bg-hover);
    border-color: var(--border-hover);
}
.traffic-route {
    display: flex;
    align-items: center;
    gap: 8px;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 13px;
    color: var(--text-primary);
    font-weight: 600;
    min-width: 150px;
    direction: ltr;
}
.traffic-bar-track {
    flex: 1;
    height: 6px;
    background: var(--border-subtle);
    border-radius: 99px;
    overflow: hidden;
    margin: 0 10px;
}
.traffic-bar-fill {
    height: 100%;
    background: var(--accent-blue-gradient);
    border-radius: 99px;
    transition: width 0.4s ease;
}
.traffic-badge {
    font-size: 12px;
    font-weight: 700;
    padding: 3px 10px;
    border-radius: 99px;
    background: var(--badge-blue-bg);
    color: var(--badge-blue-text);
    white-space: nowrap;
}
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
            <div class="topbar-actions" style="display:flex; gap:10px; align-items:center;"></div>
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
                <div id="plans-dist" class="plans-grid">
                    <div style="color:var(--text-muted);font-size:13px;">Loading plans…</div>
                </div>
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
                <div class="users-table-wrap">
                <table class="users-table">
                    <thead><tr>
                        <th style="width:24%;">User</th>
                        <th style="width:10%;">Role</th>
                        <th style="width:10%;">Status</th>
                        <th style="width:10%;">Plan</th>
                        <th class="sortable" style="width:11%;" onclick="usersView.setSort('ai_credits')">AI Credits <span id="sort-ai_credits"></span></th>
                        <th class="sortable" style="width:9%;" onclick="usersView.setSort('leads_count')">Leads <span id="sort-leads_count"></span></th>
                        <th class="sortable" style="width:12%;" onclick="usersView.setSort('created_at')">Joined <span id="sort-created_at"></span></th>
                        <th class="th-actions" style="width:14%;">Actions</th>
                    </tr></thead>
                    <tbody id="users-body"><tr><td colspan="8" style="text-align:center;color:var(--text-muted);padding:24px;">Loading…</td></tr></tbody>
                </table>
                </div>
                <div id="pager" class="pagination-wrap"></div>
            </div>

            <div class="panel-section">
                <div class="panel-header"><div><h3 class="panel-title" data-i18n="users.traffic_title">Traffic — Top Paths</h3>
                <div class="panel-desc" data-i18n="users.traffic_desc">Internal dashboard traffic log (7 days)</div></div></div>
                <div id="traffic-box"><div style="color:var(--text-muted);font-size:13px;">Loading…</div></div>
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
        document.getElementById('kpi-users').textContent = d.users_total ?? 0;
        document.getElementById('kpi-signups').textContent = d.signups_7d ?? 0;
        document.getElementById('kpi-views').textContent = d.traffic_views_7d ?? 0;
        document.getElementById('kpi-leads').textContent = d.leads_total ?? 0;
        document.getElementById('kpi-ai').textContent = d.ai_calls ?? 0;

        const dist = d.plan_distribution || {};
        const total = Math.max(d.users_total || 0, 1);
        const planMeta = {
            'free': { name: 'Free', icon: '🌱', color: 'var(--accent-blue, #2563eb)', bg: 'rgba(37, 99, 235, 0.12)' },
            'starter': { name: 'Starter', icon: '⚡', color: '#10b981', bg: 'rgba(16, 185, 129, 0.12)' },
            'growth': { name: 'Growth', icon: '🚀', color: '#8b5cf6', bg: 'rgba(139, 92, 246, 0.12)' },
            'scale': { name: 'Scale', icon: '👑', color: '#f59e0b', bg: 'rgba(245, 158, 11, 0.12)' }
        };
        const allKeys = Array.from(new Set([...Object.keys(planMeta), ...Object.keys(dist)]));
        const html = allKeys.map(k => {
            const m = planMeta[k] || { name: k, icon: '📦', color: '#64748b', bg: 'rgba(100, 116, 139, 0.12)' };
            const count = dist[k] || 0;
            const pct = Math.round((count / total) * 100);
            return `
                <div class="plan-card">
                    <div class="plan-card-header">
                        <span class="plan-name-wrap">
                            <span>${m.icon}</span>
                            <span>${m.name}</span>
                        </span>
                        <span class="plan-badge" style="background:${m.bg};color:${m.color};">${pct}%</span>
                    </div>
                    <div class="plan-count-row">
                        <span class="plan-count">${count}</span>
                        <span class="plan-sub">user${count === 1 ? '' : 's'}</span>
                    </div>
                    <div class="plan-progress-track">
                        <div class="plan-progress-fill" style="width:${pct}%;background:${m.color};"></div>
                    </div>
                </div>`;
        }).join('');
        const distEl = document.getElementById('plans-dist');
        if (distEl) distEl.innerHTML = html || '<div style="color:var(--text-muted);font-size:13px;">No users yet</div>';
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
                    <td>
                        <div style="font-weight:600;color:var(--text-primary);line-height:1.3;">${escapeHtml(u.email)}</div>
                        <div style="color:var(--text-muted);font-size:11.5px;margin-top:2px;">${escapeHtml(u.full_name || '—')}</div>
                    </td>
                    <td>${u.role === 'admin' ? '<span class="badge badge-plan">ADMIN</span>' : '<span class="badge badge-secondary" style="text-transform:uppercase;font-size:11px;">user</span>'}</td>
                    <td><span class="badge ${u.is_active ? 'badge-ok' : 'badge-off'}">${u.is_active ? 'Active' : 'Disabled'}</span></td>
                    <td><span class="badge badge-plan">${escapeHtml(u.plan || 'free')}</span></td>
                    <td id="credits-${u.id}" style="font-weight:600;font-variant-numeric:tabular-nums;">${u.ai_credits}</td>
                    <td style="font-weight:600;font-variant-numeric:tabular-nums;">${u.leads_count}</td>
                    <td style="font-size:12px;color:var(--text-secondary);font-variant-numeric:tabular-nums;">${String(u.created_at || '').slice(0, 10) || '—'}</td>
                    <td class="td-actions">
                        <div class="actions-wrap">
                            <button class="btn btn-ghost" style="padding:5px 9px;font-size:11.5px;" onclick="openCreditsModal('${u.id}')">+ Credits</button>
                            <button class="btn btn-ghost" style="padding:5px 9px;font-size:11.5px;" onclick="cyclePlan('${u.id}', '${u.plan || 'free'}')">Plan ▸</button>
                            ${u.role !== 'admin' ? `<button class="btn ${u.is_active ? 'btn-danger' : 'btn-primary'}" style="padding:5px 9px;font-size:11.5px;" onclick="toggleActive('${u.id}', ${u.is_active})">${u.is_active ? 'Disable' : 'Enable'}</button>` : ''}
                        </div>
                    </td>
                </tr>`).join('');
        }

        const pager = document.getElementById('pager');
        const prevText = window.hudhudI18n ? window.hudhudI18n.t('users.btn_prev') : '‹ Prev';
        const nextText = window.hudhudI18n ? window.hudhudI18n.t('users.btn_next') : 'Next ›';
        pager.innerHTML = `
            <span><strong>${rows.length}</strong> user(s) · page <strong>${this.page}</strong> of <strong>${pages}</strong></span>
            <div class="pagination-btns">
                <button class="btn btn-secondary" style="padding:6px 14px; font-size:12.5px;" ${this.page <= 1 ? 'disabled' : ''} onclick="usersView.goto(${this.page - 1})">${prevText}</button>
                <button class="btn btn-secondary" style="padding:6px 14px; font-size:12.5px;" ${this.page >= pages ? 'disabled' : ''} onclick="usersView.goto(${this.page + 1})">${nextText}</button>
            </div>`;
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
        const maxHits = Math.max(...entries.map(e => e[1])) || 1;
        box.innerHTML = '<div class="traffic-list">' + entries.map(([p, c]) => {
            const pct = Math.max(6, Math.round((c / maxHits) * 100));
            return `
                <div class="traffic-item">
                    <div class="traffic-route">
                        <span class="badge" style="font-size:10.5px; padding:2px 6px; background:var(--bg-card); color:var(--text-secondary); border:1px solid var(--border-default);">GET</span>
                        <span>${escapeHtml(p)}</span>
                    </div>
                    <div class="traffic-bar-track">
                        <div class="traffic-bar-fill" style="width: ${pct}%;"></div>
                    </div>
                    <div class="traffic-badge">${c.toLocaleString()} views</div>
                </div>`;
        }).join('') + '</div>';
    } catch (e) { console.error(e); }
}

document.addEventListener('DOMContentLoaded', () => { loadOverview(); loadUsers(); loadTraffic(); });
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

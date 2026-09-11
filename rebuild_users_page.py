"""Rebuild /users page on the standard shared chrome (saas.css) — Wave 9.8 UI unification."""
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
P = "src/modules/admin_users_page/__init__.py"
src = open(P, encoding="utf-8").read()

NEW_HTML = r'''_ADMIN_USERS_HTML = """<!DOCTYPE html>
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
<script>'''

m = re.search(r'_ADMIN_USERS_HTML = """.*?<script>', src, re.DOTALL)
assert m, "HTML head block not found"
src = src[:m.start()] + NEW_HTML + src[m.end():]

# drop the now-redundant closing chrome tags of the OLD document (the old tail after the script)
old_tail = '''</script>
</body>
</html>"""'''
new_tail = '''</script>
</body>
</html>"""'''
src = src.replace(old_tail, new_tail)  # unchanged; tail kept

open(P, "w", encoding="utf-8").write(src)
import ast
ast.parse(src)
print("/users rebuilt on shared chrome + syntax OK")

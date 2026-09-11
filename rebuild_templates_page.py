"""Rebuild /templates page on the standard shared chrome — Wave 9.8 UI unification."""
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
P = "src/modules/templates_manager/__init__.py"
src = open(P, encoding="utf-8").read()

NEW_HEAD = r'''_ADMIN_TEMPLATES_HTML = """<!DOCTYPE html>
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
                <span class="crumb-current">Message Templates</span>
            </div>
            <div class="topbar-actions" style="display:flex; gap:10px; align-items:center;">
                <button type="button" class="lang-switcher-btn" onclick="window.hudhudI18n.toggle()">
                    <span data-i18n="lang.switch_btn">🌐 العربية</span>
                </button>
            </div>
        </header>
        <div class="app-content">
            <div class="panel-section" style="margin-bottom:14px;">
                <div class="panel-header"><div>
                    <h3 class="panel-title">Automatic Message Templates</h3>
                    <div class="panel-desc">Edit the automatic messages your platform sends (signup, trials, plans, credits, new leads). Placeholders fill automatically at send time.</div>
                </div></div>
            </div>
            <div id="tpl-list"><div style="color:var(--text-muted);">Loading…</div></div>
        </div>
    </main>
</div>
<script src="/static/i18n.js"></script>
<script src="/static/saas.js"></script>
<script>'''

# Replace everything from the variable start to the first <script> (old head+chrome)
m = re.search(r'_ADMIN_TEMPLATES_HTML = """.*?<script>', src, re.DOTALL)
assert m, "templates HTML head block not found"
src = src[:m.start()] + NEW_HEAD + src[m.end():]

open(P, "w", encoding="utf-8").write(src)
import ast
ast.parse(src)
print("/templates rebuilt on shared chrome + syntax OK")

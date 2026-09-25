import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = "src/templates/analytics.html"
src = open(p, encoding="utf-8").read()

CARD = '''
                <!-- Threads Insights (threads_manage_insights) -->
                <div class="panel-section" id="threads-insights-panel">
                    <div class="panel-header">
                        <div>
                            <h2 class="panel-title">🧵 <span data-i18n="an.threads_title">Threads Insights</span></h2>
                            <div class="panel-desc" data-i18n="an.threads_desc">Views, likes and replies across your connected Threads account — read live from the Threads API.</div>
                        </div>
                        <button class="btn-secondary" onclick="loadThreadsInsights()" data-i18n="an.threads_refresh">🔄 Refresh</button>
                    </div>
                    <div class="metrics-strip" style="margin-bottom:12px;">
                        <div class="metric-card"><div class="metric-label" data-i18n="an.threads_views">Views</div><div class="metric-val" id="th-views">—</div></div>
                        <div class="metric-card"><div class="metric-label" data-i18n="an.threads_likes">Likes</div><div class="metric-val" id="th-likes">—</div></div>
                        <div class="metric-card"><div class="metric-label" data-i18n="an.threads_replies">Replies</div><div class="metric-val" id="th-replies">—</div></div>
                    </div>
                    <div id="threads-insights-status" style="font-size:12.5px;color:var(--text-muted);"></div>
                </div>

'''

# insert right before the Executive Reports Center panel
anchor = "                <!-- Executive Reports Center -->"
assert anchor in src
src = src.replace(anchor, CARD + anchor, 1)

JS = """
        // ==================== Threads Insights (Wave 9.8) ====================
        async function loadThreadsInsights() {
            const status = document.getElementById('threads-insights-status');
            try {
                const r = await fetch('/api/threads/insights?metric=views,likes,replies');
                const d = await r.json();
                if (d.status !== 'success') {
                    status.textContent = d.reason || d.detail || 'Insights unavailable';
                    return;
                }
                const byName = {};
                (d.insights || []).forEach(row => { byName[row.name] = (row.values || [])[0]?.value ?? 0; });
                document.getElementById('th-views').textContent = byName['views'] ?? '—';
                document.getElementById('th-likes').textContent = byName['likes'] ?? '—';
                document.getElementById('th-replies').textContent = byName['replies'] ?? '—';
                status.textContent = '';
            } catch (e) { status.textContent = 'Failed: ' + e; }
        }
        document.addEventListener('DOMContentLoaded', loadThreadsInsights);
"""

# append JS inside the last <script> block
last = src.rfind("</script>")
src = src[:last] + JS + "\n" + src[last:]
open(p, "w", encoding="utf-8").write(src)
print("threads insights card + JS injected")

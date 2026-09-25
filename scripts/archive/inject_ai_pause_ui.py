import ast, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

src = open("src/templates/settings.html", encoding="utf-8").read()

js = """        // ==================== AI Master Switch (Wave 9.8) ====================
        async function loadAiPause() {
            try {
                const r = await fetch('/api/ai/pause');
                const d = await r.json();
                renderAiPause(d);
            } catch (e) { console.warn('AI pause load failed:', e); }
        }

        function renderAiPause(d) {
            const isAr = window.hudhudI18n && window.hudhudI18n.currentLang === 'ar';
            const paused = !!d.effective_paused;
            const badge = document.getElementById('ai-pause-badge');
            const btn = document.getElementById('btn-ai-pause');
            const status = document.getElementById('ai-pause-status');
            if (!badge || !btn) return;
            badge.textContent = paused
                ? (isAr ? '⏸️ الردود الآلية موقوفة' : '⏸️ AI Paused')
                : (isAr ? '✅ الردود الآلية نشطة' : '✅ AI Active');
            badge.style.background = paused ? '#fef2f2' : '#ecfdf5';
            badge.style.color = paused ? '#dc2626' : '#059669';
            btn.textContent = paused
                ? (isAr ? '▶️ إعادة تشغيل الردود الآلية' : '▶️ Resume AI Replies')
                : (isAr ? '⏸️ إيقاف الردود الآلية' : '⏸️ Pause AI Replies');
            btn.style.background = paused ? '#059669' : '#dc2626';
            btn.style.color = '#ffffff';
            const scope = (d.global_paused && d.user_paused) ? (isAr ? 'شامل + حسابك' : 'global + your account')
                : d.global_paused ? (isAr ? 'شامل (النظام)' : 'global (system)')
                : d.user_paused ? (isAr ? 'حسابك' : 'your account') : '';
            status.textContent = paused && scope ? (isAr ? `النطاق: ${scope}` : `Scope: ${scope}`) : '';
        }

        async function toggleAiPause() {
            const btn = document.getElementById('btn-ai-pause');
            const status = document.getElementById('ai-pause-status');
            btn.disabled = true;
            try {
                const cur = await (await fetch('/api/ai/pause')).json();
                const r = await fetch('/api/ai/pause', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({paused: !cur.effective_paused})
                });
                const d = await r.json();
                if (r.ok && d.status === 'success') renderAiPause(d);
                else status.textContent = (d.detail || 'Failed');
            } catch (e) {
                status.textContent = 'Failed: ' + e;
            } finally { btn.disabled = false; }
        }

        // ==================== Change password (Phase 9.9 — account security) ====================
"""

src = src.replace(
    "        // ==================== Change password (Phase 9.9 — account security) ====================",
    js, 1)

# trigger load on DOMContentLoaded — append to existing init listener if present
src = src.replace(
    "document.addEventListener('DOMContentLoaded', () => {",
    "document.addEventListener('DOMContentLoaded', () => {\n            loadAiPause();", 1)

open("src/templates/settings.html", "w", encoding="utf-8").write(src)
print("JS injected:", "loadAiPause" in src, "| DOMContentLoaded hook:", "loadAiPause();" in src)

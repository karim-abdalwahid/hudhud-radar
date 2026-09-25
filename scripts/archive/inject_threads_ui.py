import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = "src/templates/studio.html"
src = open(p, encoding="utf-8").read()

# 1. Threads platform option
old_opt = '<option value="both" data-i18n="st.platform_both">Facebook & Instagram</option>'
new_opt = old_opt + '\n                                    <option value="threads" data-i18n="st.platform_threads">🧵 Threads</option>'
assert old_opt in src
src = src.replace(old_opt, new_opt, 1)

# 2. Threads manager section at the end of the publisher pane (before its closing)
anchor = '''<div style="display:flex; justify-content:space-between; align-items:center; margin-top:14px;">
                            <div class="btn-group">
                                <button class="btn-primary" onclick="submitPost('publish_now')" data-i18n="st.publish_now_btn">🚀 Publish Now</button>'''
threads_block = '''
                        <!-- Threads Publishing (threads_content_publish / threads_delete / threads_read_replies) -->
                        <div style="border-top:1px solid var(--border-default); margin-top:16px; padding-top:14px;">
                            <div class="panel-header" style="margin-bottom:8px;">
                                <div>
                                    <h3 class="panel-title" style="font-size:14px;">🧵 Threads Publishing</h3>
                                    <div class="panel-desc">Publish text posts to your connected Threads account, view replies, or delete published posts</div>
                                </div>
                                <button class="btn-secondary" style="font-size:12px; padding:4px 10px;" onclick="loadMyThreads()">🔄 Refresh my posts</button>
                            </div>
                            <div style="display:flex; gap:10px; align-items:flex-start; margin-bottom:12px;">
                                <textarea id="threads-text" placeholder="What do you want to share on Threads?" style="flex:1; min-height:60px; padding:9px 12px; border:1px solid var(--border-default); border-radius:9px; font-family:inherit; font-size:13px; resize:vertical;"></textarea>
                                <button class="btn-primary" style="padding:10px 16px;" onclick="publishToThreads()">🚀 Publish to Threads</button>
                            </div>
                            <div id="threads-publish-status" style="font-size:12px; color:var(--text-muted); margin-bottom:8px;"></div>
                            <div id="my-threads-list"><div style="font-size:12.5px; color:var(--text-muted);">Click "Refresh my posts" to load your published threads.</div></div>
                        </div>

                        <div style="display:flex; justify-content:space-between; align-items:center; margin-top:14px;">
                            <div class="btn-group">
                                <button class="btn-primary" onclick="submitPost('publish_now')" data-i18n="st.publish_now_btn">🚀 Publish Now</button>'''
assert anchor in src
src = src.replace(anchor, threads_block, 1)

# 3. JS functions — append before the DOMContentLoaded handler in studio
init_anchor = "        document.addEventListener('DOMContentLoaded', () => {"
js = """        // ==================== Threads publishing (Wave 9.8) ====================
        async function publishToThreads() {
            const status = document.getElementById('threads-publish-status');
            const text = document.getElementById('threads-text').value.trim();
            if (!text) { status.textContent = 'اكتب نص المنشور أولاً — Write your post text first.'; return; }
            status.textContent = '⏳ Publishing…';
            try {
                const r = await fetch('/api/threads/publish', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({text})
                });
                const d = await r.json();
                if (r.ok && d.status === 'success') {
                    status.textContent = '✅ Published to Threads! (ID: ' + (d.thread_id || '') + ')';
                    document.getElementById('threads-text').value = '';
                    loadMyThreads();
                } else { status.textContent = '❌ ' + (d.detail || 'Publish failed'); }
            } catch (e) { status.textContent = '❌ ' + e; }
        }

        async function loadMyThreads() {
            const list = document.getElementById('my-threads-list');
            try {
                const r = await fetch('/api/threads/my-posts?limit=10');
                const d = await r.json();
                if (d.status !== 'success') { list.innerHTML = '<div style="font-size:12.5px;color:var(--text-muted);">' + (d.reason || d.detail || 'Unavailable') + '</div>'; return; }
                const posts = d.posts || [];
                if (!posts.length) { list.innerHTML = '<div style="font-size:12.5px;color:var(--text-muted);">No published threads yet.</div>'; return; }
                list.innerHTML = posts.map(t => `
                    <div class="tpl-card" style="margin-bottom:8px; padding:12px;">
                        <div style="display:flex; justify-content:space-between; gap:10px; align-items:flex-start;">
                            <div style="min-width:0; flex:1;">
                                <div style="font-size:13px; color:var(--text-primary);">${(t.text||'').slice(0,140)}${(t.text||'').length>140?'…':''}</div>
                                <div style="font-size:11px; color:var(--text-muted); margin-top:4px;">${(t.timestamp||'').slice(0,16).replace('T',' ')} · id: ${t.id}</div>
                            </div>
                            <div style="display:flex; gap:6px; flex-shrink:0;">
                                <button class="btn-secondary" style="font-size:11.5px; padding:4px 10px;" onclick="viewThreadReplies('${t.id}')">💬 Replies</button>
                                <button class="btn-secondary" style="font-size:11.5px; padding:4px 10px; color:#dc2626; border-color:#fecaca;" onclick="deleteMyThread('${t.id}')">🗑️ Delete</button>
                            </div>
                        </div>
                        <div id="replies-${t.id}" style="display:none; margin-top:8px;"></div>
                    </div>`).join('');
            } catch (e) { list.innerHTML = '<div style="font-size:12.5px;color:#dc2626;">Failed: ' + e + '</div>'; }
        }

        async function viewThreadReplies(threadId) {
            const box = document.getElementById('replies-' + threadId);
            if (box.style.display === 'block') { box.style.display = 'none'; return; }
            box.style.display = 'block';
            box.innerHTML = '<div style="font-size:12px; color:var(--text-muted);">Loading replies…</div>';
            try {
                const r = await fetch(`/api/threads/${threadId}/replies?limit=10`);
                const d = await r.json();
                if (d.status !== 'success') { box.innerHTML = '<div style="font-size:12px;color:#dc2626;">' + (d.detail || 'Failed') + '</div>'; return; }
                const replies = d.replies || [];
                box.innerHTML = replies.length
                    ? replies.map(x => `<div style="font-size:12.5px; padding:6px 10px; border-bottom:1px solid var(--border-default);"><strong>@${x.username || 'user'}</strong>: ${x.text || ''}</div>`).join('')
                    : '<div style="font-size:12px; color:var(--text-muted);">No replies yet.</div>';
            } catch (e) { box.innerHTML = '<div style="font-size:12px;color:#dc2626;">' + e + '</div>'; }
        }

        async function deleteMyThread(threadId) {
            if (!confirm('Delete this Threads post permanently?')) return;
            const r = await fetch(`/api/threads/${threadId}`, { method: 'DELETE' });
            if (r.ok) { loadMyThreads(); } else { const d = await r.json().catch(() => ({})); alert(d.detail || 'Delete failed'); }
        }

""" + init_anchor
assert init_anchor in src
src = src.replace(init_anchor, js, 1)

# 4. threads publishing routes are admin-gated; my-posts endpoint added to auth gates later.
open(p, "w", encoding="utf-8").write(src)

import ast
ast.parse(open("src/modules/content/routes.py", encoding="utf-8").read())  # sanity (unchanged)
import subprocess, tempfile, os
blocks = re.findall(r"<script>([\s\S]*?)</script>", src)
ok = True
for i, blk in enumerate(blocks):
    tf = tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8")
    tf.write(blk); tf.close()
    r = subprocess.run(["node", "--check", tf.name], capture_output=True, text=True)
    if r.returncode != 0:
        ok = False
        print(f"block {i} ERROR:", r.stderr[:200])
print("studio threads UI injected | all JS blocks:", "OK" if ok else "ERRORS")

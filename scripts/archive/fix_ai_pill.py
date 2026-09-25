"""Class-D fix: inbox AI pill was a hardcoded LIE ('Active (avg 3.4s)' even
when paused). New: real /api/inbox/agent-status endpoint computing AI state +
genuine avg reply latency from stored message pairs; badge reads it live."""
import ast
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 1) backend endpoint
p = "src/modules/inbox_onboarding/__init__.py"
src = open(p, encoding="utf-8").read()
addition = '''

@router.get("/api/inbox/agent-status", tags=["Live Inbox"])
async def get_inbox_agent_status(request: Request):
    """Honest AI-operational state for the inbox pill: effective pause flag +
    average reply latency + agent replies in last 24h — computed from real
    stored message pairs (zero fabrication: None avg when no data exists)."""
    from datetime import timedelta
    from src.ai.pause import is_ai_paused
    from src.core.auth import SESSION_COOKIE_NAME, verify_session_token
    session = verify_session_token(request.cookies.get(SESSION_COOKIE_NAME) or "") if request else None
    user_id = (session or {}).get("sub")

    msgs = supabase_db.select("messages") or []
    by_lead: dict = {}
    for m in msgs:
        by_lead.setdefault(m.get("lead_id"), []).append(m)
    durs = []
    now = datetime.now(tz.utc)
    replies_24h = 0
    for lst in by_lead.values():
        lst.sort(key=lambda x: x.get("sent_at") or "")
        for a, b in zip(lst, lst[1:]):
            if a.get("sender_type") == "lead" and b.get("sender_type") == "agent" \\
                    and a.get("sent_at") and b.get("sent_at"):
                try:
                    t1 = datetime.fromisoformat(str(a["sent_at"]).replace("Z", "+00:00"))
                    t2 = datetime.fromisoformat(str(b["sent_at"]).replace("Z", "+00:00"))
                    d = (t2 - t1).total_seconds()
                    if 0 < d < 86400:
                        durs.append(d)
                except Exception:
                    pass
    for m in msgs:
        if m.get("sender_type") == "agent" and m.get("sent_at"):
            try:
                t = datetime.fromisoformat(str(m["sent_at"]).replace("Z", "+00:00"))
                if now - t <= timedelta(hours=24):
                    replies_24h += 1
            except Exception:
                pass
    return {
        "status": "success",
        "ai_paused": is_ai_paused(user_id),
        "avg_reply_seconds": round(sum(durs) / len(durs), 1) if durs else None,
        "replies_last_24h": replies_24h,
    }

'''
anchor = "@router.post(\"/api/inbox/conversations/{lead_id}/takeover\""
assert anchor in src
i = src.find("class TakeoverPayload") if "class TakeoverPayload" in src else 0
# insert right before the takeover route
idx = src.find(anchor)
src = src[:idx] + addition.lstrip("\n") + "\n" + src[idx:]
open(p, "w", encoding="utf-8").write(src)
ast.parse(src)
print("1) /api/inbox/agent-status added")

# 2) frontend badge -> live pill (same markup/design, dynamic text)
p2 = "src/templates/inbox.html"
t2 = open(p2, encoding="utf-8").read()
old_badge = '<span class="badge badge-success" data-i18n="inbox.ai_active_pill">⚡ Auto-Reply: Active (avg 3.4s)</span>'
new_badge = '<span class="badge badge-success" id="ai-state-pill" data-i18n="inbox.ai_active_pill">⚡ Auto-Reply: Active</span>'
assert old_badge in t2
t2 = t2.replace(old_badge, new_badge, 1)

# JS: fetch + render + 60s refresh
js_fn = '''
        // ===== AI state pill: honest live status (pause state + measured latency) =====
        async function refreshAiPill() {
            try {
                const r = await fetch('/api/inbox/agent-status');
                const d = await r.json();
                const pill = document.getElementById('ai-state-pill');
                if (!pill) return;
                const isAr = window.hudhudI18n && window.hudhudI18n.currentLang === 'ar';
                if (d.ai_paused) {
                    pill.textContent = isAr ? '⏸️ الرد الآلي: موقوف — وضع البشري' : '⏸️ Auto-Reply: Paused (Human Mode)';
                    pill.className = 'badge badge-pending';
                } else {
                    const avg = d.avg_reply_seconds
                        ? (isAr ? ' (متوسط ' + d.avg_reply_seconds + ' ث)' : ' (avg ' + d.avg_reply_seconds + 's)')
                        : '';
                    pill.textContent = (isAr ? '⚡ الرد الآلي: نشط' : '⚡ Auto-Reply: Active') + avg;
                    pill.className = 'badge badge-success';
                }
            } catch (e) { /* keep static label on failure */ }
        }
        document.addEventListener('DOMContentLoaded', () => {
            refreshAiPill();
            setInterval(refreshAiPill, 60000);
        });
'''
# inject before the last </script>
last = t2.rfind("</script>")
t2 = t2[:last] + js_fn + "\n    " + t2[last:]
open(p2, "w", encoding="utf-8").write(t2)
print("2) inbox badge now live")

# 3) i18n keys: fix stale value + add paused pill key
p3 = "src/templates/static/i18n.js"
t3 = open(p3, encoding="utf-8").read()
t3 = t3.replace('"inbox.ai_active_pill": "⚡ Auto-Reply: Active (avg 3.4s)"',
                '"inbox.ai_active_pill": "⚡ Auto-Reply: Active",\n        "inbox.ai_paused_pill": "⏸️ Auto-Reply: Paused (Human Mode)"', 1)
t3 = t3.replace('"inbox.ai_active_pill": "⚡ الرد الآلي: نشط (متوسط 3.4 ث)"'
                if '"inbox.ai_active_pill": "⚡ الرد الآلي: نشط (متوسط 3.4 ث)"' in t3
                else '"inbox.ai_active_pill": "⚡ الرد الآلي: نشط (متوسط 3.4ث)"'
                if '"inbox.ai_active_pill": "⚡ الرد الآلي: نشط (متوسط 3.4ث)"' in t3
                else '"inbox.ai_active_pill"',
                '"inbox.ai_active_pill": "⚡ الرد الآلي: نشط",\n        "inbox.ai_paused_pill": "⏸️ الرد الآلي: موقوف — وضع البشري"', 1)
open(p3, "w", encoding="utf-8").write(t3)
print("3) i18n: stale 3.4s value removed, paused-pill key added")

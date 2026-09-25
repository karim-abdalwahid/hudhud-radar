import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = "src/templates/static/i18n.js"
src = open(p, encoding="utf-8").read()

EN = {
    "an.threads_title": "Threads Insights",
    "an.threads_desc": "Views, likes and replies across your connected Threads account — read live from the Threads API.",
    "an.threads_refresh": "🔄 Refresh",
    "an.threads_views": "Views",
    "an.threads_likes": "Likes",
    "an.threads_replies": "Replies",
    "set.ai_pause_title": "Pause Automatic Replies — AI Master Switch",
    "set.ai_pause_desc": "Pause the AI across ALL conversations and comment automations to manage your pages personally — new messages still appear for manual replies. Per-conversation Human Takeover stays independent.",
    "st.platform_threads": "🧵 Threads",
}
AR = {
    "an.threads_title": "تحليلات ثريدز",
    "an.threads_desc": "المشاهدات والإعجابات والردود على حساب ثريدز المرتبط — تُقرأ مباشرة من واجهة Threads.",
    "an.threads_refresh": "🔄 تحديث",
    "an.threads_views": "مشاهدات",
    "an.threads_likes": "إعجابات",
    "an.threads_replies": "ردود",
    "set.ai_pause_title": "إيقاف الردود الآلية — المفتاح الرئيسي للذكاء",
    "set.ai_pause_desc": "أوقف الذكاء الاصطناعي على مستوى كل المحادثات والتعليقات لتدير صفحاتك بنفسك — الرسائل الجديدة تستمر في الظهور للرد اليدوي. Human Takeover لكل محادثة يعمل بشكل مستقل.",
    "st.platform_threads": "🧵 ثريدز",
}

def insert_after(text, anchor_key, pairs, count):
    """Insert a key block right after the first line containing anchor_key,
    in the dictionary block #count (1=EN, 2=AR) — anchored by unique AR/EN wording."""
    i = -1
    for _ in range(count):
        i = text.find(anchor_key, i + 1)
    assert i > 0, f"anchor {anchor_key} not found (occ {count})"
    eol = text.find("\n", i)
    block = "".join(f'\n        "{k}": "{v.replace(chr(34), chr(92)+chr(34))}",' for k, v in pairs.items())
    return text[:eol] + block + text[eol:]

# anchor for EN block: the first 'inbox.ai_active_pill' line (EN dict), for AR: second occurrence
src = insert_after(src, "inbox.ai_active_pill", EN, 1)
src = insert_after(src, "inbox.ai_active_pill", AR, 2)
open(p, "w", encoding="utf-8").write(src)

r = subprocess.run(["node", "--check", p], capture_output=True, text=True)
print("node --check:", "OK" if r.returncode == 0 else r.stderr[:200])
r2 = subprocess.run([sys.executable, "audit_i18n.py"], capture_output=True, text=True)
print(r2.stdout[-500:])

import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
addition = '''

## 2️⃣3️⃣ ⭐⭐ مراجعة قائمة التقديم الفعلية (34 صلاحية من 3 لقطات داشبورد ميتا)
- **نُسخت القائمة كاملة** لملف RECORDING_MATRIX.md (صورة1: 10 · صورة2: 13 · صورة3: 11 = 34) — تتضمن ما لم يكن في خطتنا: **threads_manage_mentions** + نسخ **instagram_business_*** الستة.
- **instagram_business_* = نفس التنفيذ** عندنا (page token + IG business id) → تُصوَّر بنفس الفيديوهات.
- **threads_manage_mentions كانت فجوة حقيقية** (parser لا يعرف field mentions + الاشتراك بلا mention + الجسر جاهز أصلًا): نفذت فرع الـ parser (mention-in-comment بcomment_id + mention-in-post بpost_id + تخطي الذاتي) ووسعت auto_subscribe.
- **درس API**: اسم الحقل الصحيح `mention` مفرد — اكتشف بالفحص الحي بعد رفض الجمع (قائمة الحقول الصالحة من رسالة الخطأ نفسها).
- **إثبات حي كامل**: اشتراك mention نجح → subscribed_apps يؤكده → webhook موقّع queued=1 → Lead Audit Fan برسالة metadata type=mention → تنظيف. اختبارات test_mentions_bridge 6/6 · السويت الإجمالي 278/278.
- commmit bdc9500 + deploy verified live · مصفوفة محدثة 2f0ed03.'''
open("docs/PROJECT_REPORTS/SESSION_LOGS/2026-09-11_session.md", "a", encoding="utf-8").write(addition)
addition2 = '''

### 17. Post-Entry Addition — مراجعة التقديم الفعلي (34 صلاحية)
- القائمة الفعلية منسوخة في RECORDING_MATRIX · instagram_business_* = نفس التنفيذ · threads_manage_mentions نفذت بالكامل (parser + اشتراك mention حي + إثبات E2E + تنظيف) + درس اسم الحقل المفرد. 278/278 · bdc9500 + 2f0ed03 لايف.'''
open("PROJECT_MEMORY.md", "a", encoding="utf-8").write(addition2)
print("logged")

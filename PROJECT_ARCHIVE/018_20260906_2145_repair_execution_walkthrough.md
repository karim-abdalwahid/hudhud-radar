# [018] دليل إنجاز تنفيذ خطة الإصلاح الشاملة (Repair Execution Walkthrough)
- **التاريخ**: 2026-09-06 21:45 (UTC+3)
- **الوكيل المنفذ**: opencode (GLM)
- **الحالة**: مكتملة ✅ — 62/62 اختبار، صفر ثغرات

---

## 1. ملخص التنفيذ
تنفيذ خطة الإصلاح المكونة من 8 مراحل (موثقة في [017]) بالكامل. كل مرحلة اختُبرت فور تنفيذها، واكتشف الاختبار الآلي خطأين إضافيين حقيقيين أُصلحا فوراً.

## 2. ما تم بناؤه وإصلاحه

### المرحلة 0 — الأسرار
- إزالة GitHub PAT من `git remote` بالكامل (origin أصبح نظيفاً).
- حذف `uploaded_test.md` من git والقرص.
- ⚠️ متبقٍ على المالك: إلغاء الـ PAT القديم من github.com/settings/tokens + تدوير META_APP_SECRET من Meta console.

### المرحلة 1 — المصادقة (جديدة كلياً)
| المكوّن | الملف |
|---|---|
| جدول users + user_role_enum | `database/migrations/001_users_auth_and_security.sql` + schema.sql |
| تشفير PBKDF2 (390k دورة) + جلسات HMAC موقعة | `src/core/auth.py` |
| صفحة دخول/تسجيل بتصميم SendRad + **رقم الموبايل** (مع كود الدولة +20 تلقائي) | `src/templates/auth.html` |
| حماية كل الصفحات والـ APIs (Middleware) | `src/main.py` |
| أول مستخدم = Admin تلقائياً، الباقي user | `src/core/auth.py` (UserStore) |
| حماية brute-force (10 محاولات/5 دقائق) | `src/core/auth.py` (AuthAttemptLimiter) |
| شريحة المستخدم + زر خروج في الشريط الجانبي | `src/templates/static/saas.js` |
| فرض إداري server-side على /settings /identity /analytics وكل APIs التوكنات | `src/main.py` + auth.py |

### المرحلة 2 — إصلاحات النواة
1. **منع تكرار الويب هوك**: `src/core/event_dedup.py` (Supabase processed_events + ذاكرة LRU + circuit breaker)
2. **الأتمتة**: إصلاح منصة "both"، دمج rate limiter، تعليق n8n الوهمي (paused)
3. **Inbox حقيقي**: `/api/inbox/conversations` من جدول messages (صفر تلفيق)، إرسال رسائل بشرية حقيقية، إرسال رابط الحجز من الإعدادات، حذف زر "Mark Deal Won" الوهمي
4. **Human Takeover فعلي**: عمود leads.human_takeover + فحص في orchestrator قبل أي رد آلي
5. **ذاكرة المحادثة**: Gemini multi-turn (آخر 8 رسائل + system_instruction)
6. **حل الهويات**: اختيار الأعلى ثقة وليس الأول
7. **Rate Limiter حقيقي**: تحليل X-App-Usage/X-Page-Usage/X-Business-Use-Case-Usage + cooldown 60 ثانية عند 95%
8. **Retry/Backoff** على إرسال الرسائل (2 محاولات، أخطاء 5xx فقط)
9. كاش 60 ثانية لـ /api/meta/status + إبطال فوري عند تغيير التوكن
10. حذف الروابط الوهمية (hudhud.ai) والأرقام الوهمية (142/89/34)

### المرحلة 3 — Serverless
- مخزن الأتمتة → Supabase `app_settings['automations_workflows']` (القرص كاش محلي فقط)
- ملفات الحالة المنطقية أُخرجت من git tracking (.gitignore)
- `vercel.json`: cron يومي 03:00 (حد Hobby) + `CRON_SECRET` protection
- توثيق cron-job.org البديل المجاني لدقة 5 دقائق في `.env.example`

### المرحلة 4 — الذكاء الاصطناعي
- الموديل الافتراضي: gemini-2.5-flash (أسرع/أرخص من 1.5-pro المتقاعد)
- إزالة OpenAI من Onboarding (بقي في config للمستقبل)
- إزالة WhatsApp من Onboarding والـ Inbox (قرار المالك — لا بيزنس موثق)

### المرحلة 5 — ميزات v2.1
- `src/meta_api/extended_api.py`: Insights Sync (فيسبوك+إنستغرام → page_performance_metrics)، Threads API (نشر+قراءة ردود)، Marketing API (استيراد Lead Ads بمنشأ كامل + مقاييس الحملات → يفعّل جدول campaigns)
- `src/meta_api/compliance_pages.py`: صفحة سياسة الخصوصية + صفحة حذف البيانات + callback API (تجهيز Meta App Review)

### المرحلة 6 — التنظيف
- حذف: dashboard.html (1057 سطر يتيم)، src/scraping/، egg-info، uploaded_test.md
- توحيد الـ entrypoint: `main.py` هو النقطة الوحيدة، start_server.bat محدّث
- requirements.txt مثبّت بحدود عليا
- HOW_TO_RUN.md محدّث بالكامل (مسارات جديدة، صفحات جديدة، تهيئة DB)

### المرحلة 7 — الجودة
- **13 اختبار أمني جديد** (tests/test_auth_security.py): تشفير كلمات المرور، تلاعب الجلسات، دورة التسجيل/الدخول/الخروج، رفض التكرار، حماية المسارات، منع تكرار الويب هوك end-to-end
- **عزل الاختبارات**: صفر كتابة على Supabase الحية أثناء الاختبار (user store + automations + dedup كلها ذاكرة)
- **النتيجة النهائية: 62/62 اختبار نجح، pip-audit: 0 ثغرات**

## 3. أخطاء حقيقية كشفها الاختبار وأُصلحت أثناء التنفيذ
1. `/auth/me` كان يقرأ session غير ممتلئة للمسارات العامة → قراءة الكوكي مباشرة
2. صفحات الأدمن كانت محمية كوزميتيكياً فقط → فرض 403 server-side
3. EventDeduplicator كان قد يعلق على استدعاءات DB فاشلة متكررة → circuit breaker

## 4. خطوات متبقية على المالك (خارج نطاق الكود)
1. إلغاء PAT القديم: github.com/settings/tokens
2. تدوير META_APP_SECRET: Meta Developer Console → App Settings → Secret → Reset، ثم تحديثه في Vercel Environment Variables
3. إضافة `GEMINI_API_KEY` (من aistudio.google.com) إلى .env و Vercel
4. توليد `CRON_SECRET` وإضافته إلى Vercel
5. تنفيذ `database/migrations/001_users_auth_and_security.sql` في Supabase SQL Editor
6. أول تسجيل دخول عبر /login → أول حساب = Admin
7. git push + redeploy

## 5. ملاحظة أرشفة
- PROJECT_MEMORY.md: Entry 019 (خطة + تنفيذ كامل)
- هذا الملف: الدليل التسلسلي 018

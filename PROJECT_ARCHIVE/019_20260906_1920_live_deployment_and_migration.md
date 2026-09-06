# [019] دليل إنجاز النشر الحي وتطبيق الترحيل (Live Deployment & Migration Walkthrough)
- **التاريخ**: 2026-09-06 19:20 (UTC+3)
- **الوكيل المنفذ**: opencode (GLM)
- **الحالة**: مكتملة ✅ — الموقع لايف وأوتوماتيك بالكامل

---

## 1. ملخص التنفيذ
المالك وفّر صلاحيات كاملة (Vercel CLI مسجل دخول + cron-job.org API key + Supabase Access Token) فنُفذ كل شيء مباشرة دون تدخل يدوي.

## 2. النشر الحي على Vercel
| البند | القيمة |
|---|---|
| الدومين الإنتاجي | **https://hudhud-radar-steel.vercel.app** |
| المشروع | hudhud-radar (prj_yxGldzs2buJhSxS6MFdDm6K6zZtB) |
| متغيرات البيئة | **19 متغير** رُفعت (كانت صفر! الإنتاج كان يعمل بذاكرة مؤقتة فقط) |
| APP_ENV | production (كوكي آمن + تحقق HMAC صارم) |
| Python | 3.12 من .python-version |

## 3. الأتمتة عبر cron-job.org
| Job | الجدولة | الهدف |
|---|---|---|
| Hudhud Scheduler (8045365) | **كل دقيقة** (Africa/Cairo) | `/api/cron/scheduler-tick?key=CRON_SECRET` — نشر المنشورات المستحقة |
| Hudhud Insights Sync (8121501) | يومي 4 صباحاً | `/api/cron/insights-sync?key=CRON_SECRET` — سحب مقاييس الأداء |

- الـ job القديم كان يشير لرابط ميت (hudhud-amber) — أُعيد استخدامه.
- ملاحظة للوكلاء المستقبليين: API حساب cron-job.org هذا يمنع POST (إنشاء jobs جديدة) — التعديل عبر PATCH يعمل. الـ jobs الجديدة تُنشأ من لوحة الموقع.
- فحص السر يقبل `?key=` / `?secret=` لأن الخطة المجانية لا ترسل headers مخصصة.

## 4. تطبيق ترحيل قاعدة البيانات (Management API)
- Token المالك → `POST /v1/projects/{ref}/database/query` → **11/11 عبارة نجحت**.
- Runner محفوظ: `scripts/apply_migration_001.py` (idempotent — يعمل على أي قاعدة جديدة مستقبلاً).
- التحقق: **10/10 جداول موجودة** + عمود human_takeover.

## 5. 🔥 اكتشافات أمنية جوهرية أثناء التطبيق
1. **مفاتيح خاطئة الاسم**: كل من `SUPABASE_KEY` و `SUPABASE_SERVICE_ROLE_KEY` في `.env` كانا **anon** (فك تشفير JWT أثبت role=anon) — التطبيق كله عمل بدور anon منذ الإنشاء! المفتاح الحقيقي `service_role` جُلب من Management API وفُحص (role=service_role) وحُفظ في `.env` + Vercel.
2. **نمط RLS الصحيح لهذا المشروع**: سياسات `auth.role()='service_role'` تفشل (ترجع NULL خارج جلسة Supabase Auth). النمط المجرب: `USING(true) WITH CHECK(true)` + `REVOKE ALL FROM anon` + `GRANT ALL TO service_role`. طُبق على users/processed_events/app_settings/content_posts.
3. **الجداول المنشأة بـ SQL الخام لا تأخذ الـ GRANTS الافتراضية** — احتاجت `GRANT ALL ... TO service_role` صريحاً.

## 6. التحقق الحي النهائي (بعد النشر النهائي)
| الفحص | النتيجة |
|---|---|
| /health | 200 + Supabase Cloud + production |
| تسجيل حساب المالك | 200 → **role=admin** (أول حساب) |
| تسجيل الدخول | 200 + كوكي جلسة موقعة |
| /auth/me | authenticated=true, role=admin |
| /dashboard (بجلسة) | 200 |
| /settings (بجلسة admin) | 200 |
| /api/leads (بجلسة) | 200 |
| /settings بدون جلسة | 303 → /login |
| cron بالمفتاح | 200 |
| cron بدون مفتاح | 401 |

## 7. بيانات دخول المالك (لتسجيلها في مدير كلمات مرور)
- الرابط: https://hudhud-radar-steel.vercel.app/login
- البريد: karim@ebdamarketing.com (مُسجل رسمياً في قاعدة users)
- كلمة المرور: أرسلها المالك لنفسه عبر قناة آمنة (مولدة بجلسة التنفيذ)
- ⚠️ يُنصح بتغييرها من صفحة الملف الشخصي لاحقاً عند توفر الخيار.

## 8. خطوات أمان متبقية على المالك
1. إلغاء GitHub PAT القديم (github.com/settings/tokens) — إن وجد.
2. تدوير META_APP_SECRET من Meta Developer Console وإبلاغ الوكيل لتحديثه في Vercel.
3. (اختياري) إعادة توليد Supabase Access Token بعد انتهاء الجلسة لأنه شُارك في المحادثة.
4. إضافة GEMINI_API_KEY عند توفره (aistudio.google.com) — حتى تفعّل ردود الذكاء الاصطناعي الحقيقية.

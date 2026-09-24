# تقرير عزل الاختبارات وتحـصين مسار Supabase

- **رقم الأرشيف:** `017`
- **التاريخ:** `2026-09-16` (Africa/Cairo)
- **الحالة:** إصلاحات محلية مكتملة والتحقق الحي ناجح؛ ملف migration محفوظ لمزامنة تاريخ الـDDL وسياسات الحماية.

## المشكلة المثبتة

كان تشغيل الاختبارات يتصل بمشروع Supabase السحابي. فشل 5 اختبارات بـ`42501` على `content_posts` و`activity_logs`، كما أن fixture قد يكتب بيانات اختبار في قاعدة الإنتاج. التحقق من claims للمفتاح كشف أن متغير `SUPABASE_SERVICE_ROLE_KEY` الحالي يحمل دور `anon` وليس `service_role`.

## ما نُفذ

1. إضافة `pytest.ini` لحصر discovery في `tests/` ومنع التقاط `scratch/test_studio.py` الذي يتطلب Playwright.
2. إضافة `tests/conftest.py` مع `TESTING=true`، وإضافة `TESTING` إلى Settings؛ عنده يستخدم `SupabaseManager` الـin-memory database فقط.
3. إضافة `app_settings` إلى in-memory store واختبار صريح يحرس عزل قاعدة الاختبارات.
4. إضافة تحقق من مفتاح Supabase: يقبل service-role JWT أو modern `sb_secret_` فقط. في production يفشل startup بوضوح إن كان المفتاح anon بدل تشغيل writes بهوية خاطئة.
5. إنشاء migration عبر Supabase CLI: `supabase/migrations/20260915214819_secure_backend_data_api_and_settings.sql`.
   - تنشئ `app_settings`.
   - تفعّل RLS وتلغي وصول `anon` و`authenticated` المباشر.
   - تمنح CRUD لـ`service_role` فقط.
   - تحذف policy `content_posts` العامة وتحذف policies service-role غير اللازمة.
   - تحصن trigger function بـ`search_path` وتسحب execute العام.
6. تمت مواءمة `database/schema.sql` وتحديث وثيقة schema في Project Brain مع هذا contract.

## التحقق

- `pytest` الكامل مقسمًا: **46 passed** (18 + 28)، دون الوصول إلى Supabase الحي.
- `git diff --check`: ناجح.
- تحقق production مصطنع بالمفتاح الحالي: فشل startup عمدًا برسالة أن المفتاح ليس service-role؛ هذا السلوك المقصود.

## التحقق الحي بعد تصحيح المفتاح

- تم التحقق من أن المفتاح الجديد يحمل `service_role` وأن FastAPI يتصل بـSupabase Cloud.
- service role استطاع قراءة الجداول الثمانية (`leads`, `messages`, `identity_verification_queue`, `activity_logs`, `page_performance_metrics`, `campaigns`, `content_posts`, `app_settings`).
- تم فحص `anon` قراءةً فقط، وكانت جميع الجداول محجوبة بـ`42501` كما هو مطلوب.
- تم اختبار insert/read/upsert/delete على سجل مؤقت في `app_settings` وحذفه؛ لم يبق أي سجل اختبار.
- `/health` في تشغيل التطبيق الفعلي أكد `supabase_connected: true` و`database_backend: Supabase Cloud`.

## ملاحظة migration

المشروع لم يكن مربوطًا محليًا بـSupabase CLI، لذلك لم يمكن تسجيل حالة migration البعيدة عبر CLI دون كلمة مرور PostgreSQL/ربط المشروع. ملف migration يبقى مصدرًا قابلًا للتكرار لمزامنة `app_settings` وRLS/grants وحذف policy المحتوى العامة، ولا يُرسل أي سر في المحادثة أو ملفات متتبعة.

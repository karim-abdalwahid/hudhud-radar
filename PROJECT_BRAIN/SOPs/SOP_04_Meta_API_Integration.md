# 📋 SOP-04: التكامل مع Meta Graph API و Instagram
#sop #meta-api #facebook #instagram #webhooks

يحدد هذا المستند المعايير الإلزامية للتفاعل مع منصات Meta (Facebook Pages و Instagram Business Accounts).

---

## 🎯 المعايير والسياسات الرسمية

### 1. إدارة رموز الوصول (Access Tokens)
- استخدام Page Access Tokens طويلة الأجل (Long-Lived Tokens) أو System User Tokens.
- التحقق الدوري من صلاحية التوكن قبل تنفيذ أي نداءات للواجهة البرمجية عبر دالة الفحص في `src/meta_api/permissions.py`.
- عند قرب انتهاء التوكن أو حدوث خطأ صلاحية (Code 190)، يتم تسجيل تنبيه فوري في التقارير وإيقاف العمليات التي تتطلب إذناً لتفادي الفشل التراكمي.

#### 1.1 بروتوكول اشتقاق التوكن الدائم (Permanent Never-Expiring Token)
لضمان استمرارية عمل الوكيل دون انقطاع، يجب تطبيق بروتوكول التبادل التشفيري:
1. استبدال التوكن قصير الأجل بتوكن طويل الأجل (60 يوماً) عبر `/oauth/access_token?grant_type=fb_exchange_token`.
2. اشتقاق توكن الصفحة المربوط عبر `/{page_id}?fields=access_token`.
3. التحقق من أن حقل `expires_at = 0` عبر `debug_token`، مما يمنحه صفة الديمومة مدى الحياة.


### 2. حدود الاستخدام (Rate Limiting)
- مراقبة ترويسات الاستجابة من Meta:
  - `X-App-Usage`
  - `X-Page-Usage`
  - `X-Business-Use-Case-Usage`
- إذا تجاوز الاستخدام 80% من الحد المسموح، يقوم محرك `src/meta_api/rate_limiter.py` بتأخير الطلبات تلقائياً (Exponential Backoff) لحماية الحساب من الحظر.

### 3. سياسة نافذة الـ 24 ساعة (24-Hour Messaging Window)
- يسمح بإرسال ردود مجانية على رسائل المستخدمين خلال 24 ساعة فقط من آخر رسالة أرسلها المستخدم.
- إذا انقضت الـ 24 ساعة، يُمنع إرسال أي رسالة عادية، ويجب الاعتماد فقط على Message Tags المعتمدة (مثل `ACCOUNT_UPDATE` أو `CONFIRMED_EVENT_UPDATE`) أو طلب إذن صريح للمراسلة.

### 4. قيود مراسلة غير المتابعين (Instagram Direct Rules)
- يحظر نظام **HudhudRadar** محاولات المراسلة العشوائية (Spam) أو إرسال رسائل جماعية لحسابات لا تتابع الصفحة وتخالف شروط إنستغرام.
- المراسلة مقتصرة فقط على جهات الاتصال المؤهلة والمسموح بها نظاماً وقانونياً.

---

## ملحق إلزامي — اتصالات Meta/Threads لكل عميل (2026-09-16)

هذا الملحق يحكم بيئة الـSaaS الحالية ويكمل قواعد Meta السابقة:

1. أسرار التطبيق العامة فقط (مثل App Secret وWebhook verification secret) تبقى في البيئة. أمّا Page/Instagram/Threads access token التشغيلي فيخزن مشفراً في `platform_connections` تحت مالكه `user_id`.
2. جميع عمليات Graph API تستخرج التوكن من `ConnectionService` للحساب والمنصة والمالك المطابقين، بعد `assert_entitled`. يمنع تماماً الرجوع إلى `app_settings` أو `.env` كتوكِن عميل مشترك.
3. قبل معالجة webhook أو الرد، يحل النظام حساب المستلم الخارجي إلى **مالك نشط واحد فقط**. غياب المالك، أو وجود أكثر من مالك، أو اتصال revoked/expired = تسجيل آمن وتخطي العملية؛ لا إنشاء lead ولا رد ولا بحث معرفة عالمي.
4. كل صف lead/message/comment/reply/content/metric ناتج من منصة يحمل owner نفسه، وكل dedup key يكون tenant-scoped حتى لا يمنع حدث عميل حدث عميل آخر.
5. refresh/revoke/deauthorize يتعامل مع اتصال العميل المعني فقط، ولا يكشف token أو metadata حساسة في response أو log. سياسة الـ24 ساعة، rate limits، وHMAC ما زالت إلزامية فوق هذا العزل.

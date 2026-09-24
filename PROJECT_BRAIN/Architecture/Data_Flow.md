# 🌊 Data Flow — HudhudRadar
#architecture #dataflow #meta-api #supabase

يوضح هذا المستند مسار البيانات التفصيلي من لحظة وصول رسالة أو تفاعل من فيسبوك أو إنستغرام، وحتى التخزين في Supabase واتخاذ القرار الذكي.

---

## 🔄 مسار معالجة الرسائل والعملاء المحتملين (Lead Capture & Messaging Flow)

1. **الاستقبال والتأمين (Ingestion & Verification)**:
   - يصل حدث الـ Webhook من خوادم Meta إلى نقطة النهاية `/webhooks/meta`.
   - يقوم النظام بالتحقق من صحة التوقيع المشفر بمفتاح التطبيق `APP_SECRET` عبر دالة HMAC SHA-256 لمنع الهجمات الإلكترونية.
2. **الاستخراج غير الافتراضي (Zero-Assumption Extraction)**:
   - يتم استدعاء Meta Graph API لجلب البيانات المسموح بها رسمياً فقط للمرسل (`id`, `name`, `profile_pic`, `username`, `bio`).
   - لا يتم تعبئة أي حقل غير متوفر أو غير متاح قانونياً.
3. **حل الهوية والتحقق (Identity Resolution)**:
   - يفحص النظام قاعدة بيانات Supabase للبحث عن تطابقات مؤكدة (نفس `facebook_account_id` أو `instagram_account_id`).
   - إذا وجد حسابين مشتبه بارتباطهما (نفس البريد الإلكتروني أو تم رصد رابط رسمي للحساب):
     - إذا كان الارتباط مؤكداً رسمياً من إعدادات الحساب: يتم ربطهما مع توثيق ذلك في `data_provenance`.
     - إذا كان الارتباط مجرد تشابه أو احتمال دون إثبات قطعي: يُدرج فوراً في جدول `identity_verification_queue` وتتوقف عملية الدمج الآلي، في انتظار المراجعة والموافقة اليدوية من المشرف.
4. **تخزين العميل والرسالة (Lead & Message Storage)**:
   - يتم إنشاء أو تحديث سجل العميل في جدول `leads`.
   - يتم تسجيل الرسالة الجديدة في جدول `messages` مع ربطها المرجعي بالعميل `lead_id`.
5. **معالجة الوكيل الذكي (AI Response Generation)**:
   - يقوم الوكيل بفحص شرط نافذة الـ 24 ساعة (Standard Messaging Window).
   - قراءة قاعدة المعرفة المعتمدة وتوليد رد بشري طبيعي متناسق.
   - إرسال الرد عبر Meta Graph API مع تسجيل العملية والنتيجة في `activity_logs`.

---

## ملحق إلزامي — تدفق SaaS المعزول (2026-09-16)

هذا التدفق يتقدم على التدفق التاريخي أعلاه لكل event أو request إنتاجي:

1. يصل الحدث إلى webhook الصحيح ويجتاز HMAC/validation.
2. يستخرج النظام recipient business account من الحدث ويستدعي
   `ConnectionService.owner_for_account` لتحديد `user_id` واحد active.
3. إن كان الحساب مجهولاً أو ambiguous أو الاتصال revoked/expired، يسجل رفضاً
   آمناً ويتوقف؛ لا ينشئ lead ولا message ولا RAG context.
4. كل lookup للهوية وlead/message/dedup ينفذ داخل `user_id` ذاته، ثم يختم
   records الجديدة بالمالك قبل أي كتابة.
5. يمر `lead_data.user_id` إلى `conversation_engine` ثم KB. الاسترجاع يستدعي
   `match_kb_chunks(vector, text, top_k, user_id)` فقط؛ لا يوجد بحث عام.
6. يختار outbound response/publish token من اتصال المالك الدقيق بعد entitlement
   وقيود Meta (24-hour/rate limits). لا يستخدم shared credential fallback.
7. تحفظ analytics/metrics/activity/reporting تحت المستأجر نفسه، وتصدر reports
   بطلب tenant صريح فقط.

هذا يجعل اختبار عميلين مختلفين قابلاً للتتبع من حساب المستلم حتى chunk والرد
والتوكن المستخدم، ويمنع أي cross-tenant data path عند غياب معلومة الملكية.

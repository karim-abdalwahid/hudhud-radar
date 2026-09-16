# 🧩 SaaS Tenant Data Contract — الحالة التشغيلية الحالية
#schema #supabase #saas #tenant-isolation #security

> **آخر تحقق:** 2026-09-16 بعد تطبيق
> `supabase/migrations/20260916190000_harden_backend_and_remove_unowned_legacy_data.sql`.
> **الغرض:** هذا ملحق حالي قابل للتشغيل بجانب السجلات التاريخية؛ لا يمحو
> `Supabase_Database_Schema.md` أو migrations السابقة.

---

## 1. مصدر الحقيقة وحدود الوصول

- المصدر التنفيذي: ترتيب migrations المطبقة في `supabase/migrations/`.
  ملف `database/schema.sql` bootstrap تاريخي ولا يطبق منفرداً على cloud.
- FastAPI على الخادم هو عميل البيانات الإنتاجي باستخدام `service_role`.
  browser roles (`anon`, `authenticated`) لا تملك وصول Data API إلى جداول
  التطبيق أو RPCs الحساسة.
- RLS مفعّل، لكن service role يتجاوزه؛ لذلك code path يجب أن يحمل `user_id`
  ويعتمد fail-closed. RLS ليس بديلاً عن tenant filtering في التطبيق.

## 2. قاعدة الملكية

| المورد | عقد الملكية الحالي |
|---|---|
| `platform_connections` | اتصال مشفر لكل `(user_id, platform, account_id)`؛ حساب خارجي active لا يربط بأكثر من tenant. |
| `leads`, `messages`, `content_posts`, `kb_documents`, `automations_workflows` | `user_id` إلزامي؛ كل CRUD والـdedup scoped بالمالك. |
| `activity_logs`, `page_performance_metrics`, `payment_events`, `campaigns` | `user_id` إلزامي وعلاقة حذف owner cascade-safe؛ metrics unique لكل `(user_id, platform, metric_date)`. |
| `kb_chunks` | مشتقات للمستند المملوك؛ لا تقرأ خارج document owner. |
| `usage_events`, `user_entitlements`, `user_subscriptions`, `notifications` | سجلات/حالة tenant-owned؛ وجود الجدول لا يعني أن كل مسار المنتج يستهلكه بعد. |
| `site_traffic` | telemetry عام محتمل؛ لا يعد مورداً لعميل. السجلات legacy بلا مالك حذفت بموافقة المالك، لكن العمود لا يفرض ملكية لزوار public مستقبليين. |
| `processed_events` | جدول dedup تاريخي بلا owner column؛ مفاتيح المسارات الجديدة يجب أن تكون tenant-scoped ولا تعيد global key سلوكاً. |
| `app_settings` | إعداد backend عام غير سري فقط. محظور استخدامه لـMeta/Threads customer credentials أو cache/automation مشتركة. |

## 3. عقود القراءة والكتابة الحرجة

### Inbound social event

`recipient account → ConnectionService.owner_for_account → user_id → lead/message → RAG → exact tenant token`.

إذا لم يخرج owner واحد active، تتوقف العملية بأمان. لا توجد محاولة تخمين، ولا
سياق RAG عام، ولا fallback لتوكن المالك/البيئة.

### Knowledge/RAG

- `kb_documents.user_id` هو حد المعرفة.
- RPC المقبول: `match_kb_chunks(vector, text, integer, uuid)`.
- عدم وجود `user_id` أو استدعاء unscoped = no context/rejection، وليس بحثاً
  في كل chunks.

### Outbound publishing/reply

يطلب كل Graph call owner/platform/account محددين، ثم يتحقق من entitlement
ويفك token المشفر للاتصال ذاته. لا يرسل scheduler أو inbox أو automation باسم
حساب غير مطابق للمورد المملوك.

## 4. ثوابت migration والتشغيل

1. لا تعديل يدوي للإنتاج بلا migration وpre/post-flight evidence.
2. لا يخفف `NOT NULL user_id` لمورد عميل لإصلاح مؤقت؛ يعالج السبب أو يعتمد
   migration cleanup بموافقة المالك.
3. أي FK owner إلزامي يستخدم delete semantics لا تترك صفاً بلا مالك.
4. أي schema/documentation update يشير إلى migration والاختبار/التحقق الحي
   الذي يثبته، ولا يزعم أن feature مخططة قد صارت منفذة بلا دليل.

## 5. حدود تنفيذ معلومة

- عزل مسارات RAG والتوكن والـCRM/المحتوى منفذ ومتحقق.
- `usage_events` وخصم `ai_credits` أثناء الرد، وprovider selection per tenant،
  ما زالت أعمال Phase 9.4؛ لا تعتمد كضوابط فاتورة قبل تنفيذها واختبارها.
- يلزم smoke test حي بحسابين مصرح بهما عقب تدوير التوكنات والتحقق من Meta
  App Review/Advanced Access.

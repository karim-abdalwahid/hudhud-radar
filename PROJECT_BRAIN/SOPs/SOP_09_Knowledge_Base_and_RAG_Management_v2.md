# 📋 SOP-09 v2: قاعدة معرفة وRAG معزولان لكل عميل
#sop #knowledge-base #rag #saas #tenant-isolation

> **الحالة:** المرجع التشغيلي الملزم لبيئة SaaS منذ 2026-09-16.
> **العلاقة بالنسخة السابقة:** يحفظ `SOP_09_Knowledge_Base_and_RAG_Management.md`
> التاريخ والمواد المرجعية لبيزنس واحد؛ هذه النسخة تتقدم عليه في كل مسار
> يتعامل مع بيانات عميل أو رد إنتاجي.

---

## 1. الهدف وحد tenant

كل عميل يرفع معرفته، يربط حساباته، ويتلقى ردود AI مبنية على معرفته وحدها.
`user_id` ليس معلومة اختيارية أو filter تجميلياً: إنه الحد الأمني والتجاري
المطلوب في كل ingestion، retrieval، response، delete، وaudit.

**قاعدة fail-closed:** إذا لم يتوافر `user_id` موثوق من اتصال المستلم أو من
جلسة المستخدم المصرح بها، لا ينفذ RAG ولا يرد الوكيل تلقائياً ولا يبحث في
معرفة عامة أو خاصة بعميل آخر.

## 2. مصادر المعرفة المسموح بها

| المصدر | شرط الملكية | التخزين التشغيلي |
|---|---|---|
| رفع PDF/TXT/Markdown أو نص يدخله العميل | session user هو المالك | `kb_documents.user_id` ثم `kb_chunks` التابعة له |
| مزامنة Meta/Instagram | اتصال active للعميل عبر `ConnectionService` | مستندات/مقتطفات للمالك ذاته |
| role، tone، FAQ، وعروض العميل من onboarding | المالك الذي أدخلها | مستندات معرفة tenant-owned أو إعداد tenant صريح |
| ملفات repo تحت `docs/KNOWLEDGE_BASE/` | ليست بيانات تشغيلية مشتركة للعملاء | مرجع/asset تاريخي أو bootstrap فقط؛ لا تدخل رد عميل دون نسخ مملوك له ومصرح به |

لا تخزن tokens أو أسرار أو PII غير لازمة داخل النص المستوعب أو metadata.

## 3. الاستيعاب والحفظ

1. يتحقق route/service من session/owner ويقبل فقط الملف/النص المصرح به.
2. يستخرج النص بترميز آمن ويطبق حدود الحجم والأنواع وسياسة path safety؛ لا
   يُكتب ملف العميل داخل مجلد source للمشروع.
3. ينشئ مستنداً يملك `user_id`، يقسمه إلى chunks مع metadata ومصدر واضح، ثم
   يولد embeddings ويحفظ chunks المرتبطة بالمستند. الفشل يسجل بدقة ولا يترك
   document ظاهراً كأنه جاهز بلا chunks صالحة.
4. أي sync خارجي يحدد أولاً الحساب والاتصال والمالك؛ لا تقبل عملية sync
   حساباً خارجياً حراً أو token عاماً.
5. الحذف أو إعادة المعالجة يتحققان من `document.user_id == requester.user_id`؛
   حذف المستند يمس chunks التابعة له فقط وفق علاقات قاعدة البيانات.

## 4. الاسترجاع وتوليد الرد

المسار الإنتاجي الإلزامي:

```text
webhook recipient account
  → ConnectionService.owner_for_account
  → lead/message stamped with user_id
  → conversation_engine receives lead_data.user_id
  → knowledge search(query, user_id)
  → match_kb_chunks(vector, text, top_k, user_id)
  → response using only that tenant context
```

- RPC الحي المقبول هو four-argument `match_kb_chunks(vector, text, integer, uuid)`.
  لا يسمح overload ثلاثي المعاملات أو query بلا `user_id`.
- لا تعني نتيجة RAG أن النموذج يخمن: يلتزم Zero-Assumption، ويقول بوضوح إن
  المعلومة غير متاحة عند غيابها بدلاً من اختلاق سعر أو سياسة أو وعد.
- تكتيكات البيع وCTA تستخدم فقط ما وافق عليه العميل/ما هو مستوعب في معرفته،
  مع احترام نافذة Meta وسياسة handoff البشري.

## 5. العزل، الخصوصية، والحذف

- كل read/write/delete/reindex يحمل `user_id` صريحاً؛ اختبار query بلا owner
  يجب أن يعيد سياقاً فارغاً أو رفضاً آمناً.
- Data API ليس قناة للمتصفح إلى KB. backend فقط يستخدم service role، بينما
  RLS/grants لا تمنح `anon` أو `authenticated` وصولاً مباشراً.
- لا يسجل محتوى PDF أو embedding أو token كامل في logs. يسجل document id
  والمالك ونوع العملية والنتيجة والسبب غير الحساس فقط.
- عند حذف المستخدم، تتبع المعرفة علاقة cascade-safe حتى لا تتحول إلى معرفة
  بلا مالك أو تفشل عملية deletion بسبب `SET NULL` متعارض.

## 6. اختبارات قبول إلزامية

1. عميل A يرفع معرفة مميزة؛ استعلام/رسالة عميل B لا ترى أي chunk منها.
2. inbound event بحساب مستلم غير معروف أو ambiguous لا ينشئ رد AI.
3. `user_id=None` أو RPC غير scoped يفشل/يعيد فراغاً، ولا يرجع بيانات عامة.
4. client لا يستطيع حذف/تحديث مستند عميل آخر.
5. اختبار E2E لمستأجرين: connect → upload مختلف → webhook → reply، مع فحص
   أن كل token وlead وchunk وresponse ينتمي للمالك المتوقع.

## 7. حدود المرحلة الحالية

- عزل RAG ومساره في الرد الإنتاجي منفذان ومتحققان.
- عداد الاستهلاك `usage_events` وخصم `ai_credits` أثناء الرد، وكذلك اختيار
  provider لكل tenant عبر `provider_manager`، **ليسا جزءاً مكتملاً من هذا
  المسار بعد**. لا يوثق هذا الإجراء أنهما يعملان قبل تنفيذ واختبار Phase 9.4.
- أي إضافة لهذه القدرات تمر عبر [[SOP_01_New_Feature_Development]] و[[SOP_03_Database_Migrations]] وتحدث هذا الإجراء بإضافة مؤرخة.

---

## ملحق تشغيلي — 2026-09-17: سلامة runtime للرفع والـContent Studio

1. مصدر الحقيقة للمعرفة التشغيلية هو `kb_documents`/`kb_chunks` المملوكان
   للـtenant. أي كتابة محلية تحت `docs/KNOWLEDGE_BASE` best-effort للتطوير فقط؛
   failure من filesystem read-only لا يجعل رفع العميل فاشلًا، لكن failure من
   database persistence يرجع خطأ ولا يسمح بادعاء نجاح الرفع.
2. لا يستعمل endpoint بحث أو reply أو content generation cache عالميًا أو
   ملف repo كـfallback. انقطاع DB يؤدي إلى `503` للبحث أو محتوى عام لا يدعي
   حقائق activity، وليس إلى بيانات عميل آخر.
3. embedding استعلام مفقود ينتقل إلى keyword search المملوك للعميل. SQL RPC
   يجب أن يحوي guard `query_embedding IS NOT NULL` في semantic branch؛ migration
   التشغيلية الحالية هي `20260917000100_guard_null_kb_query_embedding.sql`.
4. Content Studio يستخرج owner من session فقط ثم يجلب `search_context` و
   `sales_context` للمالك نفسه قبل بناء prompt. لا يقبل `user_id` من payload.
5. استيعاب PDF/chunks المتعدد يجري في worker thread؛ دفعات Gemini bounded
   بـ32 chunk وتفشل إلى individual embedding في worker إن لزم. لا تنفذ شبكة
   embedding المتزامنة مباشرة داخل ASGI event loop.
6. اختبار قبول إضافي: filesystem يرفض الكتابة المحلية لكن DB mock يؤكد حفظ
   المستند؛ DB disconnected يرجع 503 بلا global cache؛ و`_embed()` الذي يعيد
   `None` لا يستدعي RPC الدلالي.

# تقرير مواءمة التوثيق والخطط بعد تحصين عزل العملاء

- **التاريخ:** 2026-09-16 23:28 +03:00
- **النوع:** Documentation / Plan Alignment Audit (قراءة فقط)
- **المالك:** صاحب المشروع
- **النطاق:** ملفات `PROJECT_BRAIN/`، جميع SOPs، `PROJECT_MEMORY.md`، خارطة Phase 9/10، السجل الحي، والمرجع الخارجي لـCodex.
- **قرار تنفيذ:** لا تُعدَّل SOPs أو الخطط بهذا التقرير. التحديث ينتظر موافقة صريحة من المالك بعد عرض الفروقات.

---

## 1. الحكم التنفيذي

إصلاحات `d32d9bc` وترحيل Supabase `20260916190000_harden_backend_and_remove_unowned_legacy_data.sql` **لا تعارض هدف المشروع أو الخطة المعتمدة**. بل تنفذ جوهر Phase 9/Wave 9.8: أن يكون لكل عميل اتصالاته وبياناته ومعرفته وردوده المعزولة.

الفجوة هي **انجراف توثيقي**: بعض المستندات لا تزال تصف النسخة التاريخية التي اعتمدت حسابات أو tokens أو Knowledge Base عامة، أو تسجل بنوداً منفذة كأنها مستقبلية. لا يجوز إعادة كتابة هذا التاريخ؛ التحديث الصحيح هو ملحق زمني أو نسخة SOP جديدة، مع أرشفة النسخة السابقة.

---

## 2. الفروقات الجوهرية التي تحتاج قرار تحديث

| الأولوية | المستندات | الواقع المطبق | الفجوة المطلوبة |
|---|---|---|---|
| P0 | `SOP_09`، Data Flow، Phase 9 AI | KB/RAG يتطلب `user_id` ويبحث في `kb_documents/kb_chunks` الخاصة بالـtenant فقط؛ غياب المالك يفشل بأمان. | SOP-09 ما زال يصف Knowledge Base أساسية مشتركة. ينشأ SOP-09 v2 يعرّف حدود tenant، ingestion، retrieval، deletion وtests. |
| P0 | `SOP_04`، Security Model، Data Flow | التوكنات الفعالة مشفرة داخل `platform_connections` ومقيدة بالمالك والـentitlement؛ لا fallback عالمي. | توثيق ربط Meta القديم يتكلم عن secrets/tokens عامة. يحدَّث إلى per-tenant OAuth/connection ownership وwebhook recipient resolution. |
| P0 | `Supabase_Database_Schema.md` و`database/schema.sql` التوثيقي | user ownership مفروض، `campaigns.user_id` موجود، metrics unique لكل tenant، Data API backend-only، shared settings أزيلت. | schema doc/DDL التاريخي لا يطابقان cloud والمهاجرات. يلزم source-of-truth واضح: migrations + live export ثم ملحق schema حالي؛ لا تعديل التاريخ أو اختراع schema. |
| P1 | `PHASE_9_PLAN.md` و`Development_Roadmap.md` | 9.1/9.2/9.3 وWave 9.8 الأساسية منفذة ومتحققة؛ بقي اعتماد Meta الخارجي وفحص تشغيلي للتوكنات. | البنود لا تزال موسومة "مخططة/غير منفذة". يضاف status matrix صادق مع دليل commit/test/live migration. |
| P1 | `META_APP_REVIEW_GUIDE.md` | آخر سجل رسمي يقول إن App Review قُدم في 2026-09-12 وحالته under review. | الدليل يقرأ كأنه قبل التقديم. يضاف ملحق حالة لا يزعم approval قبل التحقق من لوحة Meta. |

## 3. تحديثات حوكمة/عملية مطلوبة، لا تعارض برمجي

| المستند | الإضافة الصحيحة |
|---|---|
| SOP-01 | تسجيل حي للجلسة، ثم append-only إلى `PROJECT_MEMORY.md` والمرجع الخارجي لـCodex، بجانب توثيق الميزة. |
| SOP-03 | توضيح أن migration files هي المصدر التنفيذي، وأن `messages/activity_logs` قد تكون append-only فلا يفرض عليها `updated_at` بلا استثناء مدروس؛ توثيق live schema بعد كل migration. |
| SOP-05 | كل identity lookup/link/review محصور داخل `user_id` ذاته؛ لا search أو merge عابر للـtenant. |
| SOP-07 | تصحيح مسار الجذر القديم `HudhudRadar` إلى `hudhud-radar`، وإلزام append-only في Memory ومرجع Codex، مع عدم حذف السجل التاريخي. |
| SOP-08 | ملكية المحتوى والنشر والـscheduler والتوكن exact per tenant ولا fallback مشترك. |
| SOP-10 | أي custom snippet/settings عامة مستقبلية تسجل actor owner صريحاً ولا تصبح مخزناً لأسرار أو بيانات عميل. |
| Archive catalog | روابط قديمة تشير إلى `HudhudRadar` وتحتاج تصحيح مسار فقط، مع بقاء عناصر الأرشيف كما هي. |

SOP-02 (صلاحية التقرير ثم الإصلاح) لم يُخالف: المالك منح صراحةً الإذن بعد التقرير، ووافق صراحةً على حذف legacy ownerless data. SOP-06 وSOP-11 لا يحتاجان تغييراً بسبب إصلاحات العزل الحالية.

---

## 4. حالة خارطة الطريق كما ظهرت في الكود والسجلات

### منفذ ومثبت

1. أساس SaaS (auth، roles، platform adapters، audit/human-control) ومراحل البناء السابقة.
2. Phase 9.1: `platform_connections`، تشفير التوكن، ConnectionService، entitlement gates.
3. Phase 9.2: واجهة/wizard الربط وحالات الاتصال الأساسية.
4. Phase 9.3 + Wave 9.8: tenant ownership end-to-end في inbound webhooks، CRM، RAG، inbox، content، scheduler، automations، analytics/reports، credentials، RLS/grants؛ مطبق حيًا في migration 022 المفهومي وSupabase migration المذكور أعلاه.
5. Phase 9.5 foundation: plans/trials/entitlements وإدارة رصيد يدوية من admin موجودة.
6. Meta App Review: الإرسال موثق؛ الموافقة نفسها قرار خارجي لم يثبت بعد.

### منفذ جزئياً أو يحتاج تحققاً

1. Phase 9.4: RAG لكل عميل مكتمل. لكن لا يوجد في مسار الرد استهلاك فعلي لـ`ai_credits` أو كتابة `usage_events`، و`conversation_engine.py` ما زال يستدعي Gemini مباشرة ولا يستهلك `provider_manager.py` لاختيار provider لكل tenant. Persona/settings الدائمة لكل tenant تحتاج قرار وتنفيذ واضحين.
2. Wave 9.8 token refresh موجود، لكنه يحتاج اختباراً تشغيلياً بتوكن متصل حقيقي/cron حي؛ Embedded Signup مشروط بـMeta Advanced Access.
3. Phase 9.9 Admin tools: custom snippets وRBAC developer الحقيقية ليستا مكتملتين؛ الموجود الحالي عرض/إدارة يدوية محدودة لا يساوي تفويض developer متكامل.

### مؤجل عمداً

- Phase 10 (features متقدمة مثل platform filters/marketing automation وتوسعات المنتج) لا يبدأ قبل تثبيت عملاء حقيقيين وقرارات الخصوصية/الميزانية/الأولوية.

---

## 5. التسلسل المقترح بعد موافقة المالك

1. تحديث وثائق الحالة والـSOPs أعلاه بإصدارات/ملاحق append-only، لا حذف ولا إعادة صياغة للتاريخ.
2. تدوير Meta/Threads tokens التي كانت موجودة سابقاً في شكل shared settings، ثم التحقق من حالة Meta App Review من لوحة Meta.
3. تنفيذ smoke test حي لمستأجرين منفصلين، بحسابين حقيقيين مصرح بهما: connect → upload KB مختلف → inbound webhook → RAG/reply → لا cross-tenant data.
4. حسم Phase 9.4: هل المنتج Gemini-only في v1 أم يسمح provider لكل عميل؟ ثم ربط usage ledger/credit enforcement وpersona/settings per tenant وفق القرار.
5. بعد ذلك فقط: Phase 9.9 ثم Phase 10 حسب أولوية العملاء الفعلية.

---

## 6. سلامة الذاكرة

- `PROJECT_MEMORY.md` كان append-only في هذه الجلسة.
- عُثر على تحديث سابق للمرجع الخارجي صيغ بتعديل فقرة ختامية بدلاً من الإضافة؛ أعيد النص السابق حرفياً ثم أُلحق ملحق مؤرخ. من هذه اللحظة كلا السجلين append-only دائماً.
- هذا التقرير توثيق مرجعي، ولا ينفذ أي تعديل في SOP أو plan حتى قرار المالك.

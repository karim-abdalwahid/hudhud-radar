# Phase 9.4 — تدقيق runtime للـAI وcredits وproviders (Pass 1)

- **التاريخ:** 2026-09-16 23:50 +03:00
- **النوع:** Codebase Audit — Pass 1 (read-only)
- **صلاحية الإصلاح:** لم يبدأ أي تعديل كود أو migration. هذا التقرير يحدد
  قرار المنتج اللازم قبل Pass 2، التزاماً بـSOP-02.
- **المرجع:** Phase 9.4 في `PROJECT_BRAIN/Roadmap/PHASE_9_PLAN.md`.

---

## الحكم التنفيذي

عزل tenant في مسار inbound/RAG يعمل ويجتاز الاختبارات، لكن طبقة **تشغيل الـAI
لكل عميل** غير مكتملة: الاختيارات المعروضة في onboarding لا تغيّر LLM runtime،
ولا يوجد usage ledger أو خصم credits، كما أن توليد المحتوى لا يحمل owner أو
persona. هذا ليس تسريب بيانات بين العملاء، لكنه يمنع المنتج من تطبيق وعد
"agent مخصص لكل عميل" أو بيع credits بصدق.

## الأدلة المؤكدة

| المجال | ما يعمل | الفجوة المثبتة |
|---|---|---|
| RAG للردود | `lead_data.user_id` يصل إلى KB و`match_kb_chunks(..., user_id)`؛ unknown recipient يتوقف بأمان. | لا مشكلة عزل هنا. |
| اختيار الـBrain | migration 004 أضاف `users.agent_brain` وendpoint يعرض `/api/ai/brains`. | onboarding يضع `payload.brain` داخل `rules_and_guidelines.md` فقط؛ لا يحدّث `users.agent_brain`، ولا يوجد أي read لهذا العمود في `src/`. |
| Runtime LLM للرد | Gemini يعمل عبر `ConversationEngine._call_gemini_api`. | يستعمل دائماً `settings.LLM_PROVIDER` و`settings.LLM_MODEL` و`settings.GEMINI_API_KEY`؛ لا يقرأ اختيار العميل أو `AIProviderManager`. |
| Persona/tone/link | onboarding يخزنها داخل KB مملوك للمستأجر. | `sales_context()` يقرأ فقط sales/products/business profile، والـprompt لا يحمّل persona كتعليمات حتمية؛ أثرها احتمالي فقط عبر RAG. |
| Credits | `users.ai_credits` و`usage_events` موجودان وadmin يستطيع إضافة credits. | لا يوجد insert في `usage_events` ولا decrement أو atomic balance check في أي مسار AI. الرصيد المعروض لا يوقف أو يحاسب الاستخدام. |
| Content generation | route محمي بجلسة عامة بواسطة middleware. | `/api/content/generate` لا يستقبل `Request` أو `user_id`، ولا يمرر persona/KB/brain/credits إلى `ContentEngine`; يستخدم Gemini global مباشرة. fallback يحتوي لغة/branding عامة قد لا تناسب العميل. |
| Provider manager | registry/discovery/masking/enablement تعمل، و18 اختباراً متعلقاً به وبـRAG تمر. | هو admin-managed global registry فقط؛ لا يوجد invocation adapter ولا validation/resolution لمرجع model عند التنفيذ. تخزين provider key server-only، لكنه غير مشفر بتشفير التطبيق الحالي. |

## المخاطر حسب الأولوية

### P0 — يجب إصلاحها قبل اعتبار Phase 9.4 مكتملة

1. **Credits شكلية:** الاستهلاك غير محاسَب ولا يمكن حظر العميل المنتهي رصيده.
2. **Brain selector غير موصول:** واجهة تقول إن العميل اختار brain، لكن الرد
   الحقيقي يظل على global Gemini؛ هذا يخالف Zero-Fabrication في حالة عرضه كخيار
   فعّال.
3. **Persona ليست تعليمات runtime:** role/tone/link لا تُحقن كـsystem context
   deterministic؛ قد لا تصل إلى الرد.
4. **Content generation غير tenant-aware:** لا يحمل owner أو إعداداته أو
   رصيده، رغم أنه AI action يجب أن يخضع لنفس contract.

### P1 — يجب تضمينها في نفس pass أو مباشرة بعده

1. اختبار نموذج غير enabled/available أو مرجع model مزور؛ يجب رفضه عند الحفظ
   وعند التنفيذ، مع fallback آمن فقط حسب سياسة صريحة.
2. ledger atomic في قاعدة البيانات: concurrent requests لا يجوز أن تجعل credit
   واحد ينتج ردين. يلزم RPC/migration transaction باسم مثل
   `reserve_ai_credit`/`finalize_ai_usage` أو خصم ذري مكافئ، مع usage event
   وmetadata لا تحتوي message/KB/token.
3. provider keys تحتاج encryption-at-application-layer إذا بقيت في Supabase؛
   masking في الواجهة وحده ليس تشفيراً في التخزين.
4. fallback templates يجب أن تكون tenant-neutral أو مبنية على settings/KB
   المملوكة، لا branding ثابتاً لمنصة واحدة.

## التنفيذ المقترح بعد قرار المالك

1. إنشاء `AIExecutionService`: يحل `user_id` → `agent_brain` صالح أو default
   platform-managed → adapter provider → reply/content result موحد.
2. حفظ persona المنظّمة (role/tone/booking link) تحت المالك، وإدخالها صراحة في
   system prompt؛ تبقى KB مصدر حقائق المنتجات والأسئلة، لا بديل إعدادات runtime.
3. migration/RPC ذري للـcredit: reserve قبل external call، release عند failure،
   finalize + `usage_events` عند output ناجح. كل action ناجح = credit واحد في
   v1 ما لم يعتمد المالك تسعيراً token-based.
4. تعديل inbound conversation وcontent generation فقط لاستخدام الخدمة، ثم
   اختبارات: zero credit، race، failed call لا يخصم، اختيار Brain صحيح، persona
   A لا تصل B، content tenant A/B، وledger metadata آمن.
5. تدوير/تشفير provider keys وفق قرار النطاق، ثم full suite وsmoke test حي.

## القرار المطلوب قبل Pass 2

**التوصية العملية لـv1:** مفاتيح providers ملك للمنصة فقط (لا يرفع العميل key)،
والعميل يختار فقط model من القائمة التي فعّلها admin؛ action ناجح (AI reply أو
AI content generation) = credit واحد، والفشل أو fallback محلي مجاني ولا يخصم.

بديل أوسع: يربط كل عميل provider/key خاصاً به. هذا يحتاج encryption، OAuth/key
UX، deletion/export وسياسة billing مختلفة، وليس مجرد توصيل `agent_brain`.

## التحقق المنفذ

```text
.\.venv\Scripts\python.exe -m pytest tests\test_ai_providers.py \
  tests\test_tenant_rag_isolation.py tests\test_knowledge_base_rag.py -q
18 passed, 2 warnings
```

التحذيران deprecation في Starlette/httpx، لا failures. هذه الاختبارات لا تغطي
المسارات غير الموصولة أعلاه، لذلك لا تستخدم كإثبات لإكمال Phase 9.4.

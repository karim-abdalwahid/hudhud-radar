# KB / Content Runtime Hardening — تحقق وتنفيذ
#archive #rag #knowledge-base #content #tenant-isolation #ci

> **التاريخ:** 2026-09-17 00:13 (UTC+3)
> **الحالة:** منفذ، مختبر محليًا، وترحيل Supabase مطبق
> **المحفز:** مراجعة مستقلة طلب المالك التحقق منها ثم الإصلاح الفوري للنقاط الصحيحة.

---

## 1. نتيجة التحقق من المراجعة

| النقطة | الحكم | الدليل/النتيجة |
|---|---|---|
| كتابة upload إلى `docs/KNOWLEDGE_BASE` | صحيحة | كان `DocumentProcessor` يكتب قبل حفظ `kb_documents`؛ filesystem Vercel قد يكون read-only فيوقف الرفع قبل مصدر الحقيقة. |
| Content Studio لا يستخدم معرفة العميل | صحيحة | `/api/content/generate` كان محميًا بالجلسة، لكن لا يمرر owner إلى `ContentEngine` ولا يدخل KB في prompt. |
| global KB cache/fallback | صحيحة | `reload()` كان يقرأ كل `kb_documents` ويستخدم `filename` وحده كمفتاح، وroute البحث كان يرجع إلى cache غير معزول عند انقطاع DB. |
| `NULL` embedding يخلق ترتيبًا دلاليًا غير ذي معنى | صحيحة | كان Python يمرر `query_embedding=None` إلى RPC بينما CTE الدلالي يرتب بـ`<=> NULL`. |
| synchronous/batchless ingestion + connection scan + CI | صحيحة جزئيًا | عمليات embedding كانت تحجب endpoints async؛ `owner_for_account` يقرأ كل الاتصالات النشطة؛ لم يكن workflow فعليًا موجودًا. تنظيف ملفات الجذر مؤجل عمدًا بسبب agent آخر يعمل محليًا. |

**توضيح RLS:** نموذج Data API backend-only المتفق عليه قائم: `anon` و`authenticated`
لا يملكان جداول التطبيق، و`service_role` هو عميل backend. هذا لا يلغي ضرورة
العزل داخل Python لأن `service_role` يتجاوز RLS؛ لذلك لم نعدّه حماية كافية
وحده ولم نخفف أي grant أو policy في هذه الدفعة.

## 2. الإصلاحات المنفذة

### رفع المعرفة وVercel

- `src/knowledge/document_processor.py`: استخراج TXT/PDF/image صار مستقلًا عن
  الملف المحلي. النسخة داخل `docs/KNOWLEDGE_BASE` best-effort للتطوير فقط؛
  `OSError` يسجل دون إيقاف المعالجة، ولم يعد processor يعمل `knowledge_base.reload()`.
- `src/modules/knowledge/routes.py`: يتحقق من session owner قبل القراءة؛
  التحويل والحفظ/embedding يمران عبر `asyncio.to_thread`. إذا فشل حفظ DB يرجع
  `503` صريح ولا يعتبر الملف مرفوعًا بنجاح.
- `src/modules/inbox_onboarding/__init__.py`: حفظ business profile وguidelines
  صار worker-thread أيضًا وبفشل صريح حتى لا تعلق عملية onboarding أو تدعي نجاحًا.

### RAG وذاكرة العملاء

- `src/agent/knowledge_base.py`: DB mode لا يحمل الجدول كاملًا إلى cache ولا
  يعود إلى ملفات repo عند خطأ DB. لا توجد global context في SaaS mode.
- `/api/knowledge/search` يرفض مؤقتًا بـ`503` عند عدم اتصال Supabase؛ لم يعد
  يستدعي `semantic_engine` أو cache غير مملوك.
- `src/knowledge/db_knowledge_base.py`: عند فشل embedding للاستعلام، يستخدم
  بحث keyword scoped بالمالك مباشرة بدل RPC بمتجه `NULL`.
- migration الحية
  `supabase/migrations/20260917000100_guard_null_kb_query_embedding.sql`
  تضيف شرط `query_embedding IS NOT NULL` داخل semantic CTE كدفاع مستقل حتى
  لو استدعى RPC مستقبلًا كود آخر. المرآة المفهومية:
  `database/migrations/023_guard_null_kb_query_embedding.sql`.

### Content Studio

- route يستخرج `user_id` من session الموثق (لا يقبله من JSON).
- `ContentEngine.generate_content(..., user_id=...)` يجلب query-specific RAG
  وsales context للمالك فقط، ويضعهما داخل prompt مع منع صريح للخلط أو اختراع
  أسعار/منتجات/نبرة من عميل آخر.
- إذا لم توجد معرفة، instructs prompt نموذجًا عامًا بلا claims عن النشاط؛
  fallback المحلي لم يعد يضع هاشتاج brand تاريخي ثابت.

### الأداء وconnections وCI

- chunks غير المخزنة في cache تستخدم Gemini `batchEmbedContents` في batches
  بحد 32، ثم fallback individual داخل worker إذا لم يدعم مشروع Gemini batch.
- connection lookup يرسل exact platform/account/status filters إلى PostgreSQL؛
  Instagram linked account يستخدم JSON `metadata.contains` في DB بدلاً من scan
  كل اتصالات العملاء.
- أضيف `.github/workflows/tests.yml`: يعمل على pushes وPRs إلى `main` ببيئة
  `TESTING=true` وبدون secrets إنتاجية، ويشغل `pytest`.

## 3. التنفيذ الحي والتحقق

- نفذ `npx supabase db push --linked` بنجاح وطبق فقط:
  `20260917000100_guard_null_kb_query_embedding.sql`.
- الاختبارات المركزة: **43 passed**.
- suite كامل: **325 passed, 2 skipped, 1 warning** في 53.65 ثانية.
  الـskips المقصودة لاختبارات Threads OAuth لغياب `THREADS_APP_ID` في بيئة test.
- `python -m compileall -q src tests` و`git diff --check` مرّا؛ تحذيرات Windows
  CRLF لا تمثل فرق محتوى أو خطأ syntax.

## 4. ما لم يُدّع أنه اكتمل

1. Phase 9.4 (provider selection، persona/brain runtime، usage credit
   consumption) ما زال يحتاج قرار المنتج الموثق في archive 028؛ لم نغيّره هنا.
2. تنظيف/نقل ملفات الجذر القديمة لم ينفذ لأن local workspace مشترك مع agent
   آخر. لا حذف أو نقل ضمن هذه الدفعة.
3. يلزم لاحقًا smoke test يدوي في Vercel: upload PDF حقيقي ثم content generation
   وبحث tenant على حسابين منفصلين. الاختبارات الحالية تثبت العقود برمجيًا ولا
   تستخدم بيانات عملاء أو أسرارًا حية.

## 5. مرجع خارجي

طريقة `batchEmbedContents` المستخدمة مطابقة لوثائق Gemini الرسمية:
[Gemini embeddings REST API](https://ai.google.dev/api/embeddings).

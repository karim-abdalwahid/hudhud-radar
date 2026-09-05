# خطة تنفيذ مشروع SocailManager (AI Social Media Management Agent)
**رقم الأرشفة: 001** | **التاريخ والوقت: 2026-09-03 22:24:17+03:00** | **النوع: Implementation Plan**

---

بناء وكيل ذكاء اصطناعي متكامل واحترافي لإدارة صفحات Instagram و Facebook، مزود بقاعدة معرفة (Knowledge Base)، ونظام إدارة وتحليل متقدم، والتقاط العملاء المحتملين (Lead Capture)، وتتبع المحادثات عبر Supabase مع حل الهوية (Identity Resolution)، ونظام تقارير وإحصاءات دقيق، مع بنية تنظيمية صارمة تشمل Project Brain متوافق مع Obsidian، وسجل ذاكرة تراكمي دائم (PROJECT MEMORY)، وإجراءات تشغيل قياسية (SOPs)، ونظام تدقيق برمجي وأمني ثنائي المراحل (Two-Pass Codebase Audit).

---

## User Review Required

> [!IMPORTANT]
> **اختيار حزمة التقنيات الأساسية (Tech Stack Selection):**
> نقترح استخدام **Python 3.14 + FastAPI + Pydantic + Supabase-py + Meta Graph API SDK / HTTPX**:
> 1. **محرك الذكاء الاصطناعي وتحليل البيانات**: بايثون هي الأقوى في التعامل مع محركات الـ LLM (LangChain / Gemini / OpenAI)، وتحليل البيانات الإحصائية (Pandas / NumPy)، وتوليد التقارير المتقدمة.
> 2. **الامتثال وقابلية التوسع**: إدارة الـ Webhooks والـ Rate Limiting وهياكل البيانات الصارمة (Pydantic models) تضمن دقة بنسبة 100% للبيانات دون أي تخمين.
> 3. **البديل**: Node.js / TypeScript (Fastify / Express).
> *نوصي باعتماد بايثون (FastAPI) مع واجهة تحكم ولوحة بيانات حديثة وأنيقة (Modern Dashboard UI).*

> [!WARNING]
> **سياسات منصة Meta الرسمية (Meta Platform Policies):**
> - المحادثات عبر Direct Message تخضع لقاعدة نافذة الـ 24 ساعة (Standard Messaging Window) بعد تفاعل المستخدم، ما لم يتم استخدام رسائل مدفوعة أو علامات رسائل معتمدة (Message Tags).
> - استخراج البيانات (Scraping): لا يمكن تنفيذ أي كشط مخالف لشروط الاستخدام (Meta Terms of Service). سيتم الاعتماد حصراً على الـ APIs الرسمية ومصادر البيانات المصرح بها وقانونية تقنياً مع فحص معايير الأمان ومحددات المعدل (Rate Limits).

---

## Open Questions

> [!NOTE]
> 1. **بيئة تشغيل قاعدة بيانات Supabase**: هل يتوفر لديك مشروع جاهز على Supabase ستقوم بتزويد مفاتيحه (`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`) في ملف البيئة (`.env`)، أم تود أن نجهز سكريبتات الترحيل والتأسيس (SQL Migrations) لتقوم بتطبيقها في لوحة التحكم لديك؟
> 2. **مزود نموذج الذكاء الاصطناعي (LLM Provider)**: هل تفضل الاعتماد على Google Gemini API أم OpenAI (GPT-4o) أم واجهة مرنة تدعم الاثنين لتشغيل وكيل المحادثات وتحليل التقارير؟

---

## Proposed Changes

سيتم إنشاء هيكل المشروع بالكامل داخل المجلد:
`c:\Users\Dell\Desktop\$AI_TESTING\SocailManager`

```
SocailManager/
├── PROJECT_MEMORY.md                     # السجل الدائم والتراكمي (Append-Only) لجميع المحادثات والقرارات
├── PROJECT_BRAIN/                        # عقل المشروع المهيأ للربط مع Obsidian (Wikilinks & MOCs)
│   ├── 00_Index.md                       # الفهرس الرئيسي وخريطة المحتوى (Map of Content)
│   ├── Architecture/                     # المعمارية والنماذج البيانية
│   │   ├── System_Architecture.md
│   │   ├── Data_Flow.md
│   │   └── Security_Model.md
│   ├── SOPs/                             # إجراءات التشغيل القياسية
│   │   ├── SOP_01_New_Feature_Development.md
│   │   ├── SOP_02_Codebase_Audit_Two_Pass.md
│   │   ├── SOP_03_Database_Migrations.md
│   │   ├── SOP_04_Meta_API_Integration.md
│   │   └── SOP_05_Manual_Identity_Verification.md
│   ├── Schemas/                          # هياكل الجداول وقواعد البيانات
│   │   └── Supabase_Schema_Spec.md
│   └── Roadmap/                          # خريطة الطريق والتطور المستمر
│       └── Development_Roadmap.md
├── docs/
│   ├── PROJECT_REPORTS/                  # تقارير التدقيق البرمجي والنشاط
│   │   ├── AUDIT_LOG.md
│   │   └── ACTIVITY_EXECUTION_LOG.md
│   └── KNOWLEDGE_BASE/                   # قاعدة المعرفة الخاصة بالنشاط التجاري والصفحات
│       ├── brand_tone.md
│       ├── faqs.md
│       └── rules_and_guidelines.md
├── database/
│   └── schema.sql                        # سكريبت ترحيل Supabase (جداول leads, messages, verification_queue, metrics)
├── src/
│   ├── __init__.py
│   ├── config.py                         # إعدادات التطبيق والمتغيرات البيئية ومحددات المنصات
│   ├── core/
│   │   ├── logger.py                     # نظام تسجيل وتوثيق شامل للعمليات
│   │   ├── supabase_client.py            # عميل الاتصال بقاعدة بيانات Supabase
│   │   └── exceptions.py                 # تصنيفات مخصصة للأخطاء والاستثناءات
│   ├── meta_api/
│   │   ├── client.py                     # عميل Meta Graph API لفيسبوك وإنستغرام
│   │   ├── webhooks.py                   # معالج أحداث Webhook للرسائل والتفاعلات
│   │   ├── rate_limiter.py               # نظام إدارة وتتبع حدود الاستخدام وتفادي الحظر
│   │   └── permissions.py                # التحقق من الصلاحيات والتوكنات
│   ├── identity/
│   │   ├── extractor.py                  # استخراج البيانات المتاحة فقط بدون افتراضات
│   │   ├── resolver.py                   # حل الهوية وتحديد درجة التطابق (Confidence Scoring)
│   │   └── review_queue.py               # إدارة طابور المراجعة اليدوية والتأكيد البشري
│   ├── leads/
│   │   ├── service.py                    # خدمة إدارة العملاء المحتملين ومزامنتهم
│   │   └── models.py                     # نماذج Pydantic للعملاء والرسائل ومصدر البيانات
│   ├── agent/
│   │   ├── orchestrator.py               # منسق وكيل الذكاء الاصطناعي الرئيسي
│   │   ├── knowledge_base.py             # قارئ ومحلل قاعدة المعرفة
│   │   └── conversation_engine.py        # محرك الردود الذكي المتوافق مع السياسات
│   ├── analytics/
│   │   ├── statistics_engine.py          # تحليل أسباب النجاح والفشل والأنماط التراكمية
│   │   └── page_performance.py          # قياس مؤشرات الأداء (KPIs) لصفحات فيسبوك وإنستغرام
│   ├── reporting/
│   │   ├── report_generator.py           # مولد التقارير الشاملة
│   │   └── activity_reporter.py          # تقارير النشاط والعمليات المنفذة
│   ├── scraping/
│   │   ├── base_scraper.py               # هيكل الكشط وجمع البيانات القانوني والمصرح به
│   │   └── compliance.py                 # مدقق الامتثال للسياسات والشروط
│   └── main.py                           # خادم التطبيق والـ API ونقاط نهاية الـ Webhooks
├── tests/
│   ├── __init__.py
│   ├── test_identity_resolution.py       # اختبارات دقة مطابقة الهويات ومنع التخمين
│   ├── test_rate_limiter.py              # اختبارات عدم تجاوز محددات المنصة
│   └── test_lead_capture.py              # اختبارات تخزين العملاء والرسائل
├── requirements.txt                      # مكتبات المشروع
└── .env.example                          # نموذج المتغيرات البيئية والمفاتيح السرية
```

---

## Detailed Components Design

### 1. قاعدة البيانات والتقاط العملاء (Supabase Database Design)
سيتم إنشاء الجداول التالية مع الروابط الدقيقة وقيود التكامل المرجعي:
- `leads`:
  - `id` (UUID, Primary Key)
  - `source` (enum: 'facebook', 'instagram', 'manual', 'other')
  - `full_name`, `username`, `profile_url`, `bio`, `location`, `contact_email`, `contact_phone`
  - `facebook_account_id`, `instagram_account_id`
  - `linked_account_id` (UUID - للإشارة إلى حساب آخر مؤكد يخص نفس الشخص)
  - `data_provenance` (JSONB - تفاصيل مصدر كل معلومة، توقيت الجمع، وهل تم التحقق منها يدوياً أم آلياً)
  - `created_at`, `updated_at`
- `messages`:
  - `id` (UUID, Primary Key)
  - `lead_id` (UUID, Foreign Key -> leads.id, ON DELETE CASCADE)
  - `platform` (enum: 'facebook', 'instagram')
  - `platform_message_id` (مُعرف الرسالة على المنصة)
  - `sender_type` (enum: 'lead', 'agent', 'admin')
  - `content` (نص الرسالة أو المرفقات)
  - `sent_at`, `delivered_at`, `read_at`
  - `metadata` (JSONB)
- `identity_verification_queue`:
  - `id` (UUID, Primary Key)
  - `primary_lead_id`, `candidate_lead_id`
  - `match_reason` (سبب الاشتباه بالربط)
  - `confidence_score` (نسبة التأكد الآلية)
  - `status` (enum: 'pending', 'approved', 'rejected')
  - `reviewed_by`, `reviewed_at`
- `activity_logs`:
  - `id` (UUID)
  - `action_type`, `platform`, `target_id`, `status` ('success', 'failed', 'in_progress')
  - `error_reason`, `details` (JSONB), `executed_at`
- `page_performance_metrics`:
  - `id`, `platform`, `date`, `reach`, `impressions`, `engagement_rate`, `follower_count`, `leads_generated`

### 2. محرك حل الهوية وتتبع المنشأ (Identity Resolution & Provenance)
- تطبيق قاعدة صارمة: **منع التخمين أو التوليد الافتراضي للبيانات (Zero Assumption Policy)**.
- إذا لم تكن البيانات متوفرة بشكل صريح وقانوني، تُترك الحقول فارغة (`None`/`NULL`).
- عند وجود حساب فيسبوك مرتبط بحساب إنستغرام:
  - إذا كان الرابط مؤكداً رسمياً من إعدادات المنصة، يتم الربط مع تسجيل ذلك في `data_provenance`.
  - إذا وجد تشابه في الاسم أو المعرف فقط دون دليل رسمي، يتم إدراج الحالة فوراً في `identity_verification_queue` وتنبيه المستخدم للمراجعة والاعتماد البشري الصريح.

### 3. وكيل الذكاء الاصطناعي وقاعدة المعرفة (AI Agent & Knowledge Base)
- قراءة ملفات المعرفة من `docs/KNOWLEDGE_BASE/` (نبرة البراند، إجابات الأسئلة الشائعة، شروط العروض).
- محرك استجابة يفحص:
  1. هل الحساب ضمن نافذة الـ 24 ساعة؟
  2. هل المستخدم متابع للحساب (في حال إنستغرام) وما هي قيود المراسلة المعمول بها؟
  3. إنتاج رد طبيعي وإنساني متناسق مع المعرفة المخزنة.
  4. استخلاص أي بيانات يقدمها العميل داخل المحادثة وتخزينها كبيانات مستخرجة وموثقة.

### 4. الإحصاءات والتقارير المعمقة (Analytics & Performance Reports)
- **ما الذي نجح وما الذي فشل ولماذا**: ربط كل رسالة وحملة بنتيجتها مع تصنيف سبب الفشل (محددات المعدل، رفض الطرف الآخر، تجاوز النافذة الزمنية، أخطاء في التوكن).
- **تقارير دورية مجهزة**: تقارير النمو، التفاعل، العملاء المحتملين، ومعدل التحويل.

### 5. عقل المشروع المتوافق مع Obsidian (PROJECT BRAIN)
- استخدام نظام الروابط الداخلية المزدوجة `[[wikilinks]]`.
- ملف `00_Index.md` مركزي يربط جميع مكونات النظام، الإجراءات، الجداول، والخرائط.
- إمكانية فتح مجلد `PROJECT_BRAIN` كـ Vault مباشر داخل برنامج Obsidian للتصفح البياني (Graph View).

### 6. ذاكرة المشروع التراكمية (PROJECT MEMORY)
- ملف `PROJECT_MEMORY.md` محمي بقاعدة صارمة: **Append-Only** (إضافة فقط ولا حذف ولا تعديل على السابق).
- توثيق كل طلب من المستخدم وكل رد وقرار تقني وتاريخه بالساعة والدقيقة لضمان استمرارية السياق إلى الأبد.

### 7. نظام التدقيق ثنائي المراحل (Two-Pass Codebase Audit)
- تنفيذ قاعدة التدقيق البرمجي الإلزامية بعد أي تطوير:
  - **المرحلة الأولى (Pass 1 - العرض والتقرير)**: فحص الأمان (مفاتيح، ثغرات)، الحزم والتبعيات (`pip-audit` / `safety`)، التكرار، والتحسينات، وعرضها في جداول منظمة مع انتظار موافقة المستخدم.
  - **المرحلة الثانية (Pass 2 - الإصلاح)**: تطبيق الإصلاحات المعتمدة فقط مع إعادة الاختبار والتحقق.

---

## Verification Plan

### الفحص الآلي (Automated Verification):
1. اختبار تجميع الملفات وبناء التطبيق والتحقق من صحة الاستيراد والنحو (Syntax & Type checking).
2. اختبارات وحدة لـ:
   - خوارزمية حل الهوية وعدم الدمج التلقائي عند انخفاض نسبة التأكد (`test_identity_resolution.py`).
   - قيود معدل المراسلة والتزام نافذة الـ 24 ساعة (`test_rate_limiter.py`).
   - استخراج وتخزين العملاء المحتملين وتتبع المنشأ (`test_lead_capture.py`).
3. تدقيق الاعتماديات بحثاً عن الثغرات الأمنية (`safety check` أو `pip audit`).

### الفحص اليدوي (Manual Verification):
1. مراجعة هيكل المجلدات المنشأة داخل `SocailManager`.
2. معاينة ملفات `PROJECT_MEMORY.md` و `PROJECT_BRAIN/00_Index.md` وتناسق الروابط في Obsidian.
3. مراجعة سكريبت قاعدة بيانات Supabase والتأكد من مطابقة جميع الحقول والمتطلبات.

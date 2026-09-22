# 🧠 HudhudRadar — Project Brain (MOC)
#project-brain #social-manager #meta-agent #index

مرحباً بك في **عقل المشروع (Project Brain)** المخصص لنظام **HudhudRadar**. تم تصميم هذا العقل ليعمل كـ Map of Content (MOC) متوافق بالكامل مع **Obsidian** ويدعم الروابط التشعبية المزدوجة `[[wikilinks]]` والرسوم البيانية للعلاقات (Graph View).

---

## 🗺️ خريطة المحتوى والملاحة السريعة

### 1. 🏗️ المعمارية والتصميم الهندسي
- [[System_Architecture]] — المعمارية الشاملة والمكونات الأساسية للنظام.
- [[Data_Flow]] — مسار تدفق البيانات من Meta Webhooks إلى Supabase ولوحة التحكم.
- [[Security_Model]] — معايير الأمان، عزل المفاتيح، الصلاحيات، وحماية الخصوصية.
- [[CALM_MINIMAL_DESIGN_SYSTEM]] — دليل نظام التصميم الهادئ، الألوان، الخطوط، وفلسفة Linear & Vercel.

### 2. 📋 إجراءات التشغيل القياسية (SOPs)
- [[SOP_01_New_Feature_Development]] — كيفية إضافة ميزة جديدة خطوة بخطوة دون تكرار كود.
- [[SOP_02_Codebase_Audit_Two_Pass]] — بروتوكول التدقيق الأمني والبرمجي الإلزامي ثنائي المراحل.
- [[SOP_03_Database_Migrations]] — معايير ترحيل وتعديل جداول Supabase.
- [[SOP_04_Meta_API_Integration]] — قواعد التكامل مع Meta Graph API و Instagram Graph API.
- [[SOP_05_Manual_Identity_Verification]] — بروتوكول حل الهوية والمراجعة اليدوية للبيانات المشكوك بها.
- [[SOP_06_Skill_Discovery_and_Integration]] — بروتوكول استكشاف وتقييم وتثبيت المهارات الذكية (Skills CLI).
- [[SOP_07_Document_Archiving_and_Versioning]] — بروتوكول أرشفة وترقيم الخطط والوثائق التاريخية لمنع الفقدان.
- [[SOP_08_Content_Publishing_and_AI_Scheduling]] — معايير صناعة وجدولة ونشر المحتوى بالذكاء الاصطناعي ويدوياً (بوستات، ريلز، استوري).
- [[SOP_09_Knowledge_Base_and_RAG_Management]] — بروتوكول سحب محتوى ميتا، هندسة قاعدة المعرفة والـ RAG، والاستيعاب متعدد الوسائط وتكتيكات إغلاق المبيعات.
- [[SOP_09_Knowledge_Base_and_RAG_Management_v2]] — المرجع التشغيلي لـRAG المعزول لكل عميل في SaaS؛ يتقدم على النسخة التاريخية عند التعامل مع بيانات العملاء.
- [[SOP_10_Custom_Code_Injection]] — قواعد حقن الأكواد المخصصة في header/body من لوحة الأدمن: التخزين، الأمان، الحذف الفوري، والتدقيق.
- [[SOP_11_PowerShell_Command_Safety]] — قاعدة دائمة: ممنوع أوامر Python/Node الطويلة inline في PowerShell — كل أمر معقد ملف سكربت.


### 3. 💾 هياكل البيانات وقاعدة البيانات
- [[Supabase_Database_Schema]] — مواصفات جداول `leads`، `messages`، `verification_queue`، وسجلات الأداء.
- [[SaaS_Tenant_Data_Contract]] — عقد الملكية/الوصول الحالي للجداول والـRAG والتوكنات بعد tenant hardening.

### 4. 🚀 خريطة التطوير والتحسين المستمر
- [[Development_Roadmap]] — مراحل البناء الحالية والمستقبلية وتوسعات المنصات الأخرى.
- [[PHASE_9_PLAN]] — خطة المنصة متعددة المستخدمين (SaaS) — موجات 9.1-9.8 بحالتها.
- [[PHASE_10_PLAN]] — خطة ما بعد الإطلاق: الإعلانات والأفلييت (مؤجلة بشروط).
- [[ADMIN_TOOLS_PLAN]] — أدوات إدارة الموقع: أدوار المستخدمين (admin/developer/user) + حقن الأكواد المخصصة (Wave 9.9).
- **الحالة التنفيذية الحالية:** Phase 9 الأساسية منفذة؛ 9.4/credits/provider integration جزئية، Meta Advanced Access خارجي، وWave 9.9/Phase 10 backlog. راجع [[PHASE_9_PLAN]].

- **ملحق 2026-09-20:** صفحة Account ومسار OAuth والتجربة ثلاثية الأيام تحصّنت محليًا؛ تأكيد Polar/Vercel production smoke وقرار الإلغاء ما زالا مطلوبين. راجع [[PHASE_9_PLAN]] وarchive 030.

### 5. 📜 السجلات والذاكرة الدائمة والأرشيف
- [[PROJECT_MEMORY]] — الرابط لسجل الذاكرة الدائم غير القابل للمسح.
- [[000_ARCHIVE_CATALOG]] — فهرس وسجل الأرشيف التاريخي الشامل المرتب تسلسلياً.
- [[Activity_Logging_Standard]] — معايير تسجيل العمليات والأخطاء والتحليل السببي.

---

## 🧭 القواعد الجوهرية للنظام
1. **سياسة عدم التخمين (Zero-Assumption Data Policy)**: لا اختلاق أو افتراض لأي معلومة عن العميل المحتمل.
2. **الامتثال التام لسياسات المنصات**: احترام نافذة الـ 24 ساعة ومحددات المعدل (Rate Limits).
3. **التوثيق الدائم**: كل قرار، ميزة، أو خطأ يوثق فوراً في التقارير وسجل الذاكرة.
4. **سلامة الأوامر**: ممنوع أوامر Python/Node الطويلة inline في PowerShell — كل أمر معقد يُكتب ملف سكربت ([[SOP_11_PowerShell_Command_Safety]]).

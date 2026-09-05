# 📚 تقرير الأرشفة 011: نظام قاعدة المعرفة الذكية والـ RAG والاستيعاب متعدد الوسائط وتكتيكات إغلاق المبيعات
#archive #knowledge-base #rag #multimodal #gemini-vision #sales-closing #meta-scraping

- **المعرف التسلسلي**: `011`
- **التاريخ والوقت**: `2026-09-04 10:30 UTC+3`
- **نوع الوثيقة**: ميزة جوهرية وبنية تحتية معرفية (Core Architecture & AI Feature)
- **الحالة**: مكتمل ومختبر 100% (Completed & Verified)
- **المؤلف**: مهندس الذكاء الاصطناعي (AI Assistant)

---

### 1. ملخص الميزة المنفذة (Executive Summary)
بناء نظام متكامل لإدارة واستيعاب المعرفة بتقنية **RAG (Retrieval-Augmented Generation)** وسحب المحتوى التاريخي من حسابات فيسبوك وإنستغرام الخاصة بـ **كريم عبد الواحد (@karim__abdalwahid / إبدأ ماركتينج)**.
يتيح النظام للذكاء الاصطناعي دراسة النشاط التجاري بالكامل، استخلاص الخدمات والأسعار، واستخدام تكتيكات إغلاق المبيعات (Sales Closing Tactics) في الرد على تعليقات واستفسارات العملاء والرسائل المباشرة لتحويل المتابعين إلى صفقات مؤكدة، مع إمكانية استيعاب ملفات النصوص والـ PDF والصور الإعلانية بالرؤية البصرية (Gemini Vision)، وتوفير محرر مباشر داخل لوحة التحكم مع التحديث اللحظي للذاكرة (Live Hot-Reload).

---

### 2. المكونات المنجزة برمجياً (Technical Implementation Details)

#### 2.1 محرك سحب بيانات ميتا والتحليل المعرفي (`src/knowledge/meta_crawler.py`)
- **`MetaContentCrawler`**:
  - جلب منشورات صفحة فيسبوك التاريخية والتعليقات المصاحبة: `GET /{page_id}/feed?fields=id,message,created_time,story,attachments,comments.limit(20){message}`.
  - جلب مواد إنستغرام والريلز والتعليقات: `GET /{ig_user_id}/media?fields=id,caption,media_type,media_url,permalink,timestamp,comments.limit(20){text}`.
  - تجميع موحد للنصوص والكابشن وتعليقات المتابعين.
- **`BusinessKnowledgeSynthesizer`**:
  - صياغة وتوليد 5 ملفات رئيسية بالذكاء الاصطناعي (أو بالمحرك التحليلي الحتمي كاحتياطي):
    1. `business_profile.md`: هوية ورسالة النشاط التجاري والقيمة التنافسية.
    2. `products_and_services.md`: باقات الإعلانات، إنتاج الريلز الفيروسية، وأنظمة الرد الذكي.
    3. `sales_scripts_and_closing.md`: نصوص وتكتيكات إغلاق البيع، الرد على اعتراضات الأسعار، وطريقة حث العميل على ترك هاتفه.
    4. `audience_insights.md`: تحليل رغبات واهتمامات المتابعين من واقع التعليقات الحقيقية.
    5. `synced_meta_history.md`: سجل توثيقي بالمنشورات والريلز المحللة.

#### 2.2 معالج المستندات متعددة الصيغ والرؤية البصرية (`src/knowledge/document_processor.py`)
- **ملفات Markdown والنصوص (`.md`, `.txt`)**: تنظيف النصوص وحفظها مباشرة مع تحديث الكاش.
- **ملفات PDF (`.pdf`)**: استخراج النصوص صفحة بصفحة باستخدام `pypdf` وتنسيقها في Markdown مع البيانات الوصفية.
- **الصور والإنفوجرافيك (`.png`, `.jpg`, `.jpeg`, `.webp`)**: تحويل الصورة لـ Base64 واستدعاء **Gemini Multimodal Vision** بموجه استراتيجي لاستخراج العروض، الأسعار، الخدمات، وأرقام التواصل وصياغتها في وثائق `visual_*.md`.

#### 2.3 توسيع مدير قاعدة المعرفة والـ RAG (`src/agent/knowledge_base.py`)
- دعم عمليات `list_documents()`, `get_document()`, `save_document()`, `delete_document()`.
- استرجاع السياق ذو الصلة `search_relevant_chunks(query, top_k=3)` عبر مطابقة الكلمات المفتاحية وأوزان أسئلة المبيعات والأسعار.
- سياق إغلاق المبيعات المباشر `get_sales_closing_context()`.
- إعادة تحميل لحظي (Hot-Reload) للذاكرة عند أي تعديل أو حفظ بدون إعادة تشغيل السيرفر.

#### 2.4 محرك المحادثات وإغلاق المبيعات (`src/agent/conversation_engine.py`)
- دمج تكتيكات البيع المعتمدة: الرد على استفسار "بكام / السعر" بالتأكيد على وجود باقات مخصصة وطلب رقم الهاتف للتواصل المباشر.
- الرد التلقائي على كلمة ה-CTA في الريلز ("ابدأ") بإرسال الخطة وطلب الهاتف/البريد.
- تحويل العميل المحتمل فورياً عند استلام رقم الهاتف أو البريد (`is_converted=True`).

#### 2.5 نقاط النهاية الجديدة في الـ API (`src/main.py`)
- `POST /api/knowledge/sync-meta`: تشغيل سحب وتحليل محتوى ميتا وتحديث قاعدة المعرفة.
- `GET /api/knowledge/documents`: استعراض قائمة ملفات المعرفة مع حجمها وعدد كلماتها وحالتها.
- `GET /api/knowledge/documents/{filename}`: قراءة محتوى وثيقة محددة.
- `PUT /api/knowledge/documents/{filename}`: حفظ التعديلات وإعادة تحميل الذاكرة فورياً.
- `POST /api/knowledge/documents`: إنشاء وثيقة جديدة.
- `DELETE /api/knowledge/documents/{filename}`: حذف وثيقة.
- `POST /api/knowledge/upload`: رفع ومعالجة المستندات والصور بـ Multipart Form Data.

#### 2.6 واجهة استوديو المعرفة والـ RAG في لوحة التحكم (`/dashboard`)
- تبويب جديد ومخصص: **"📚 استوديو المعرفة والـ RAG (Knowledge Studio)"**.
- شريط إجراءات ومؤشرات KPI حية (عدد الوثائق، إجمالي الكلمات، حالة الذاكرة).
- مستكشف بطاقات الوثائق مع شارات التمييز (ركيزة أساسية، مسحوب من ميتا، رؤية بصرية).
- محرر Markdown مباشر مدمج في المتصفح مع زر الحفظ اللحظي وإشعار Toast.
- منطقة رفع تفاعلية تدعم سحب وإفلات الملفات والصور مع شروحات المعالجة.

---

### 3. الاختبارات والتحقق (Testing & Verification)
- إنشاء ملف الاختبارات الشامل: [`tests/test_knowledge_base_rag.py`](file:///c:/Users/Dell/Desktop/$AI_TESTING/SocailManager/tests/test_knowledge_base_rag.py).
- **النتيجة**:
  - `7 passed in 13.71s (100%)` لاختبارات المعرفة والـ RAG.
  - `28 passed in 24.29s (100%)` لكامل مشروع SocailManager بدون أي أخطاء أو انكسارات.
- تشغيل خادم التطوير الحي على `http://127.0.0.1:8000` والتأكد من استجابة `/api/knowledge/documents` بـ 9 وثائق معرفية نشطة.

---

### 4. الربط مع عقل المشروع والإجراءات القياسية
- صياغة وتفعيل الإجراء القياسي: [`PROJECT_BRAIN/SOPs/SOP_09_Knowledge_Base_and_RAG_Management.md`](file:///c:/Users/Dell/Desktop/$AI_TESTING/SocailManager/PROJECT_BRAIN/SOPs/SOP_09_Knowledge_Base_and_RAG_Management.md).
- تحديث فهرس عقل المشروع: [`PROJECT_BRAIN/00_Index.md`](file:///c:/Users/Dell/Desktop/$AI_TESTING/SocailManager/PROJECT_BRAIN/00_Index.md).
- تحديث فهرس الأرشيف الشامل: [`PROJECT_ARCHIVE/000_ARCHIVE_CATALOG.md`](file:///c:/Users/Dell/Desktop/$AI_TESTING/SocailManager/PROJECT_ARCHIVE/000_ARCHIVE_CATALOG.md).
- تحديث سجل الذاكرة الدائم: [`PROJECT_MEMORY.md`](file:///c:/Users/Dell/Desktop/$AI_TESTING/SocailManager/PROJECT_MEMORY.md).

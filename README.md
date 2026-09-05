# ⚡ HudhudRadar (AI Social Media Management Agent)

نظام متطور وشامل لإدارة وتشغيل صفحات **Facebook** و **Instagram** بالكامل بواسطة وكيل ذكاء اصطناعي مستقل، متصل بقاعدة بيانات **Supabase (PostgreSQL)**، ومزود بمحرك إحصاءات متقدم وتحليل سببي، ونظام التقاط عملاء محتملين بدون أي تخمين (Zero-Assumption Identity Resolution)، ونظام حوكمة وتوثيق مدعوم بـ **Project Brain** متوافق مع **Obsidian**.

---

## 🌟 الميزات الجوهرية للنظام

1. **التحليلات والإحصاءات المتقدمة (Root-Cause Analytics)**:
   - تحديد ما نجح وما فشل والسبب الجذري الدقيق للفشل (انتهاء نافذة الـ 24 ساعة، بلوغ محددات المعدل، أخطاء التوكن).
   - رصد الأنماط والاتجاهات التراكمية وتوليد توصيات تشغيلية قابلة للتنفيذ.
2. **تقارير أداء الصفحات (Performance Reports)**:
   - تقارير شاملة لمعدلات النمو، الوصول (Reach)، الظهور (Impressions)، ومعدلات التحويل (Conversion Rate).
3. **تقارير الأنشطة والتنفيذ (Execution Logs)**:
   - سجل تدقيق غير قابل للتعديل يوثق كل عملية، توقيتها، حالتها، وأسباب فشلها بالتفصيل.
4. **التقاط العملاء وإدارة المحادثات (Lead Capture & Messaging)**:
   - جداول علائقية منفصلة ومترابطة في Supabase: `leads` و `messages`.
   - استخراج حقيقي للبيانات بدون افتراضات أو اختلاق (Zero Data Fabrication).
   - حل الهويات الذكي: كشف الحسابات المشتركة وربطها آلياً إذا توفر إثبات رسمي قطعي.
   - طابور مراجعة بشري (`identity_verification_queue`) للحالات المشكوك بها لمنع الدمج الخاطئ.
   - تتبع المنشأ الكامل لكل معلومة (`data_provenance`).
5. **الامتثال لسياسات المنصات ومكافحة السبام**:
   - احترام نافذة الـ 24 ساعة لرسائل فيسبوك وإنستغرام.
   - نظام Rate Limiting ذكي لحماية الحسابات من الحظر.
   - كشط واستخراج بيانات مقيد بالقنوات الرسمية والقانونية والمصرح بها فقط.
6. **Project Brain متوافق مع Obsidian**:
   - مجلد `PROJECT_BRAIN/` يمكن فتحه مباشرة كـ Vault داخل Obsidian للتصفح البياني (Graph View) والروابط المزدوجة `[[wikilinks]]`.
7. **ذاكرة المشروع التراكمية (PROJECT MEMORY)**:
   - ملف `PROJECT_MEMORY.md` تراكمي ودائم (Append-Only) لا يُحذف منه شيء.

---

## 🏗️ هيكلية المشروع (Project Structure)

```
HudhudRadar/
├── PROJECT_MEMORY.md                     # السجل التراكمي الدائم (Append-Only)
├── PROJECT_BRAIN/                        # عقل المشروع لـ Obsidian
│   ├── 00_Index.md                       # الفهرس الرئيسي (MOC)
│   ├── Architecture/                     # المعمارية ومسار البيانات
│   ├── SOPs/                             # إجراءات التشغيل القياسية (SOP-01 to SOP-05)
│   ├── Schemas/                          # مواصفات جداول Supabase
│   └── Roadmap/                          # خريطة الطريق
├── docs/
│   ├── PROJECT_REPORTS/                  # تقارير النشاط والتدقيق
│   └── KNOWLEDGE_BASE/                   # قاعدة المعرفة (نبرة البراند، الأسئلة، القواعد)
├── database/
│   └── schema.sql                        # سكريبت ترحيل Supabase الشامل
├── src/
│   ├── config.py                         # إعدادات النظام والمتغيرات البيئية
│   ├── core/                             # السجلات الآمنة، استثناءات، عميل Supabase
│   ├── meta_api/                         # عميل Meta Graph API، ويب هوك، Rate Limiter
│   ├── identity/                         # المستخرج الحقيقي، حل الهوية، طابور المراجعة
│   ├── leads/                            # نماذج وخدمات إدارة العملاء والمحادثات
│   ├── agent/                            # منسق الوكيل، قاعدة المعرفة، محرك الردود
│   ├── analytics/                        # محرك الإحصاءات والتحليل السببي
│   ├── reporting/                        # مولد التقارير الشاملة
│   ├── scraping/                         # جمع البيانات والامتثال
│   └── main.py                           # خادم FastAPI ولوحة التحكم التفاعلية
└── tests/                                # الاختبارات الآلية الشاملة
```

---

## 🚀 طريقة التشغيل والتهيئة

### 1. إعداد البيئة الافتراضية وتثبيت المكتبات
```bash
python -m venv venv
# تفعيل البيئة (Windows PowerShell):
.\venv\Scripts\Activate.ps1

# تثبيت الاعتماديات:
pip install -r requirements.txt
```

### 2. ضبط المتغيرات البيئية
انسخ ملف `.env.example` إلى `.env` وقم بتعبئة بياناتك:
```bash
cp .env.example .env
```

### 3. إعداد جداول Supabase
- افتح لوحة تحكم مشروعك في [Supabase](https://supabase.com).
- انتقل إلى **SQL Editor**.
- الصق محتويات ملف `database/schema.sql` واضغط **Run**.

### 4. تشغيل الاختبارات الآلية
```bash
pytest -v
```

### 5. تشغيل الخادم ولوحة التحكم
```bash
python src/main.py
```
- لوحة التحكم التفاعلية: `http://localhost:8000/dashboard`
- وثائق الـ API التفاعلية (Swagger): `http://localhost:8000/docs`
- فحص الحالة: `http://localhost:8000/health`

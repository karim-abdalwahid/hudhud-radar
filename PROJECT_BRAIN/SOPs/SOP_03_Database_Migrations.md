# 📋 SOP-03: إدارة وترحيل قواعد البيانات (Database Migrations)
#sop #database #supabase #postgresql #migrations

يحدد هذا المستند المعايير الصارمة لإنشاء وتعديل جداول ومخططات قاعدة بيانات Supabase لنظام **HudhudRadar**.

---

## 🎯 المبادئ الأساسية
1. **التكامل المرجعي الصارم (Foreign Key Integrity)**: جميع العلاقات بين الجداول (مثل `messages` المرتبطة بـ `leads`) يجب أن تستخدم مفاتيح أجنبية محكمة مع خيارات الحذف أو التحديث المحددة بوضوح (`ON DELETE CASCADE` أو `SET NULL`).
2. **منع فقدان البيانات**: لا يتم حذف أي أعمدة أو جداول نشطة دون إنشاء نسخة احتياطية وموافقة صريحة من المستخدم.
3. **الفهارس المخصصة للأداء (Indexes)**: إنشاء فهارس على الحقول المستخدمة في الاستعلامات المتكررة (مثل `platform`, `sender_type`, `created_at`, `primary_lead_id`).
4. **تتبع المنشأ والوقت**: كل جدول يحتوي إلزامياً على `created_at` و `updated_at` مع Trigger تلقائي لتحديث `updated_at`.

---

## 🛠️ هيكلية الترحيل
- يتم حفظ المخطط الشامل والأساسي في `database/schema.sql`.
- عند إضافة أي تعديل مستقبلي، يتم حفظ التعديل في ملف فرعي مؤرخ مثل `database/migrations/YYYYMMDD_feature_name.sql` وتحديث الملف الرئيسي.
- يتم تحديث مواصفات المخطط فوراً في عقل المشروع: [[Supabase_Database_Schema]].

---

## ملحق إلزامي — مصدر الحقيقة وعزل المستأجرين (2026-09-16)

1. **المصدر التنفيذي للحقيقة** هو تسلسل ملفات migrations المطبقة في Supabase، وليس ملف bootstrap منفرداً. أي تغيير حي يوثق بملف migration قابل للمراجعة، ثم يُشار إليه في مواصفة الـschema الحالية.
2. لا يعدل production يدوياً بلا migration. قبل التنفيذ: preflight للـFK/الـnull rows/الـduplicates؛ وبعده: postflight يعدّ النتائج ويتحقق من grants/RLS عند تأثر الوصول.
3. بيانات موارد العميل (CRM، messages، knowledge، content، automations، metrics، payments، campaigns) تحمل `user_id` صريحاً وملكية قابلة للتحقق. لا يجوز جعلها nullable أو إنشاء مسار query/write غير مفلتر إلا إذا كان المورد public telemetry موثقاً صراحة.
4. `ON DELETE` يجب أن ينسجم مع القيد: علاقة owner إلزامية تستخدم cascade أو إجراء حذف صريحاً آمناً، ولا يجوز `SET NULL` إذا صار العمود `NOT NULL`.
5. قاعدة `updated_at` لا تنطبق قسراً على سجلات append-only مثل الرسائل وسجل التدقيق؛ يوضح سبب الاستثناء في migration/schema بدلاً من تغيير معنى السجل التاريخي.
6. عند تغير contract تشغيلي، يُحدّث [[Supabase_Database_Schema]] و[[SaaS_Tenant_Data_Contract]]. ملف `database/schema.sql` هو bootstrap تاريخي ما لم يُحدّث من تسلسل migrations كاملاً؛ لا يُشغّل وحده لافتراض حالة cloud الحالية.

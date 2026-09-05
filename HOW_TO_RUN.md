# 🚀 دليل التشغيل السريع — HudhudRadar (Run Guide)

دليل شامل ومبسط يشرح لك كيفية تشغيل واستخدام وفحص نظام **HudhudRadar** لإدارة صفحات فيسبوك وإنستغرام.

---

## ⚡ الطريقة الأسهل والأسرع (ضغطة زر واحدة)

لقد قمنا بإنشاء ملفات تشغيل تلقائية جاهزة داخل المجلد:
1. **لتشغيل السيرفر ولوحة التحكم مباشرة**: اضغط مرتين (Double Click) على الملف:
   👉 `start_server.bat`
2. **لتشغيل كافة الاختبارات الآلية**: اضغط مرتين على الملف:
   👉 `run_tests.bat`

---

## 🖥️ التشغيل اليدوي عبر سطر الأوامر (PowerShell / Terminal)

إذا أردت تشغيل المشروع من سطر الأوامر، اتبع الخطوات التالية:

### الخطوة 1: فتح موجه الأوامر داخل مجلد المشروع
افتح **PowerShell** وتوجه لمجلد المشروع:
```powershell
cd 'c:\Users\Dell\Desktop\$AI_TESTING\HudhudRadar'
```

### الخطوة 2: تشغيل الخادم (Server)
قم بتشغيل هذا الأمر المباشر:
```powershell
.\.venv\Scripts\python.exe src/main.py
```
أو عبر تفعيل البيئة الافتراضية أولاً:
```powershell
.\.venv\Scripts\Activate.ps1
python src/main.py
```

بمجرد ظهور الرسالة التالية، يكون السيرفر يعمل بنجاح:
```
INFO: HudhudRadar AI Engine is running and ready to manage pages.
INFO: Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

---

## 🌐 الروابط المباشرة للاستخدام في المتصفح

بعد تشغيل السيرفر، افتح متصفحك واذهب إلى:

| الوجهة | الرابط المباشر | الوصف |
| :--- | :--- | :--- |
| **لوحة التحكم التنفيذية** | [http://localhost:8000/dashboard](http://localhost:8000/dashboard) | تصفح العملاء، المحادثات، طابور المراجعة اليدوية، والتحليلات والتقارير. |
| **واجهة Swagger التفاعلية** | [http://localhost:8000/docs](http://localhost:8000/docs) | تجربة واستدعاء كافة وظائف الـ API ونقاط الـ Webhook مباشرة. |
| **فحص حالة النظام (Health)** | [http://localhost:8000/health](http://localhost:8000/health) | التأكد من اتصال قاعدة البيانات وحالة جهوزية الوكيل. |

---

## 🧪 فحص واختبار الكود (Unit Tests)

للتأكد في أي وقت من سلامة كافة وظائف النظام وخلوه من أي خلل:
```powershell
.\.venv\Scripts\pytest.exe -v
```
*(ستظهر لك نتيجة نجاح الـ 12 اختباراً بنسبة 100%)*.

---

## 🛑 إيقاف الخادم
لإيقاف السيرفر في أي وقت:
اضغط على الاختصار **`Ctrl + C`** داخل نافذة التيرمينال.

---

## ⚙️ إعداد بيانات Supabase و Meta الحقيقية

النظام مهيأ تلقائياً للعمل في وضع التطوير المحلي (In-Memory Dev Store) بدون توقف. للربط مع حساباتك السحابية الحقيقية:
1. انسخ ملف `.env.example` إلى `.env`:
   ```powershell
   Copy-Item .env.example .env
   ```
2. ضع مفاتيح Supabase الخاصة بك:
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_ROLE_KEY`
3. قم بتطبيق سكريبت الترحيل الكامل في Supabase SQL Editor:
   - انسخ محتويات الملف: [`database/schema.sql`](./database/schema.sql) واضغط **Run**.
4. ضع بيانات صفحة فيسبوك وتوكن الوصول:
   - `META_PAGE_ACCESS_TOKEN`
   - `META_APP_SECRET`
   - `META_PAGE_ID`

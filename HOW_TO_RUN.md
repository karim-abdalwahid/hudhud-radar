# 🚀 دليل التشغيل السريع — HudhudRadar (Run Guide)

دليل شامل ومبسط يشرح لك كيفية تشغيل واستخدام وفحص نظام **HudhudRadar** لإدارة صفحات فيسبوك وإنستغرام.

> ⚠️ **تنبيه مهم (2026-09-06)**: النظام الآن محمي بنظام تسجيل دخول.
> أول حساب تسجله عبر `/register` يصبح **مدير النظام (Admin)** تلقائياً — احتفظ ببيانه جيداً!

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
cd 'C:\Users\Dell\Desktop\OpenCodeProjects\hudhud-radar'
```

### الخطوة 2: تشغيل الخادم (Server)
قم بتشغيل هذا الأمر المباشر:
```powershell
.\.venv\Scripts\python.exe main.py
```
أو عبر تفعيل البيئة الافتراضية أولاً:
```powershell
.\.venv\Scripts\Activate.ps1
python main.py
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
| **تسجيل الدخول / إنشاء حساب** | [http://localhost:8000/login](http://localhost:8000/login) | البوابة الرئيسية — أول حساب يصبح Admin |
| **لوحة التحكم التنفيذية** | [http://localhost:8000/dashboard](http://localhost:8000/dashboard) | نظرة عامة (تتطلب تسجيل دخول) |
| **صندوق المحادثات الحي** | [http://localhost:8000/inbox](http://localhost:8000/inbox) | محادثات حقيقية + تولي بشري فعلي |
| **واجهة Swagger التفاعلية** | [http://localhost:8000/docs](http://localhost:8000/docs) | تجربة واستدعاء كافة وظائف الـ API |
| **فحص حالة النظام (Health)** | [http://localhost:8000/health](http://localhost:8000/health) | التأكد من اتصال قاعدة البيانات (عام بدون دخول) |
| **سياسة الخصوصية** | [http://localhost:8000/privacy](http://localhost:8000/privacy) | صفحة عامة (متطلب Meta App Review) |
| **حذف البيانات** | [http://localhost:8000/data-deletion](http://localhost:8000/data-deletion) | صفحة عامة (متطلب Meta App Review) |

---

## 🗄️ تهيئة قاعدة البيانات (مرة واحدة)

1. افتح لوحة تحكم مشروعك في [Supabase](https://supabase.com).
2. انتقل إلى **SQL Editor**.
3. الصق محتويات ملف [`database/schema.sql`](./database/schema.sql) كاملاً واضغط **Run**.
   - يحتوي الآن على: الجداول الأساسية + `users` (المصادقة) + `processed_events` (منع التكرار) + `app_settings` (إعدادات السحابة).
4. إذا كانت قاعدة بياناتك قائمة بالفعل وتحتاج فقط الجداول الجديدة، نفّذ بدلاً من ذلك:
   - [`database/migrations/001_users_auth_and_security.sql`](./database/migrations/001_users_auth_and_security.sql)

---

## 🧪 فحص واختبار الكود (Unit Tests)

للتأكد في أي وقت من سلامة كافة وظائف النظام وخلوه من أي خلل:
```powershell
.\.venv\Scripts\pytest.exe -v
```
*(62 اختباراً — من بينها اختبارات المصادقة والأمان ومنع تكرار الويب هوك — جميعها معزولة عن قاعدة البيانات الحية)*.

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
3. قم بتطبيق سكريبت الترحيل الكامل في Supabase SQL Editor (انظر قسم تهيئة قاعدة البيانات أعلاه).
4. ضع بيانات صفحة فيسبوك وتوكن الوصول:
   - `META_PAGE_ACCESS_TOKEN`
   - `META_APP_SECRET`
   - `META_PAGE_ID`
5. **مهم للإنتاج (Vercel)**: أضف متغير `CRON_SECRET` بقيمة عشوائية طويلة لحماية نقاط الـ Cron.

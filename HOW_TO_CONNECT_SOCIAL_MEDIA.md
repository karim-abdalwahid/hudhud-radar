# 🌐 دليل ربط صفحات فيسبوك وإنستغرام بحساب Meta Developers خطوة بخطوة

هذا الدليل يشرح لك بالتفصيل ومن الصفر كيف تسجل دخول وتربط حساباتك الرسمية في فيسبوك وإنستغرام بوكيل الذكاء الاصطناعي **HudhudRadar**.

---

## 💡 لماذا لا نستخدم اسم مستخدم وكلمة مرور عادية؟
منصة Meta (فيسبوك وإنستغرام) تحظر تماماً الدخول بكلمة المرور وتعتبره روبوت غير شرعي يعرض حسابك للحظر الفوري. الطريقة الرسمية والقانونية الوحيدة والآمنة 100% التي تدعمها Meta هي عبر **Meta Graph API** وتوليد **Page Access Token**.

---

## 🛠️ الخطوات العملية خطوة بخطوة (من الصفر):

### الخطوة 1: التسجيل في منصة مطوري ميتا (Meta for Developers)
1. افتح الرابط: **[https://developers.facebook.com](https://developers.facebook.com)**
2. سجل دخولك بحسابك الشخصي في فيسبوك (الحساب الذي يمتلك أو يدير الصفحة).
3. اضغط على **Get Started** أو **My Apps** في الزاوية العلوية، ثم وافق على شروط المطورين.

---

### الخطوة 2: إنشاء تطبيق جديد (Create App)
1. اضغط على زر **Create App** (إنشاء تطبيق).
2. اختر نوع التطبيق: **Business** (للأعمال).
3. أدخل اسم التطبيق: مثلاً `HudhudRadar AI`.
4. أدخل بريدك الإلكتروني واضغط **Create App**.

---

### الخطوة 3: إضافة المنتجات المطلوبة (Add Products)
في لوحة تحكم التطبيق، ستجد قائمة بالمنتجات (Add a product to your app):
1. ابحث عن **Messenger** واضغط **Set Up**.
2. ابحث عن **Instagram Graph API** واضغط **Set Up**.

---

### الخطوة 4: ربط صفحة الفيسبوك وحساب إنستغرام
1. تأكد أن حساب إنستغرام الخاص بك هو حساب احترافي (**Professional / Business Account**) ومرتبط بنفس صفحة فيسبوك من إعدادات إنستغرام.
2. في لوحة تحكم التطبيق، اذهب إلى:
   **Messenger** > **Instagram Settings** أو **Facebook Login** > **Settings**.
3. قم بربط صفحتك.

---

### الخطوة 5: توليد التوكن الدائم (Page Access Token)
أسهل وأسرع طريقة للحصول على التوكن:
1. اذهب إلى أداة مستكشف الـ API الرسمية:
   👉 **[https://developers.facebook.com/tools/explorer/](https://developers.facebook.com/tools/explorer/)**
2. في القائمة اليمنى:
   - في خانة **Meta App**: اختر تطبيقك `HudhudRadar AI`.
   - في خانة **User or Page**: اضغط واختر **صفحتك على فيسبوك** (ستظهر لك خيارات مثل: *Page Access Token*).
3. في خانة **Permissions** (الصلاحيات)، تأكد من إضافة الصلاحيات التالية:
   - `pages_show_list`
   - `pages_read_engagement`
   - `pages_manage_metadata`
   - `pages_messaging`
   - `instagram_basic`
   - `instagram_manage_messages`
4. اضغط **Generate Access Token** ووافق على الصلاحيات.
5. انسخ الـ Token الناتج (يبدأ عادة بـ `EAAB...` أو `EAA...`).

---

### الخطوة 6: إدخال البيانات في لوحة التحكم (HudhudRadar Dashboard)

افتح لوحة التحكم في متصفحك:
👉 **[http://localhost:8000/dashboard](http://localhost:8000/dashboard)**

1. اذهب إلى تبويب **"🔗 ربط حسابات السوشيال ميديا"**.
2. الصق الـ **Page Access Token**.
3. اضغط زر **"اختبار وحفظ الاتصال"**.
4. سيقوم النظام فوراً بالاتصال بسيرفرات فيسبوك، والتأكد من صحة التوكن، وعرض اسم صفحتك بعلامة خضراء 🟢!

---

## 🔄 إعداد استقبال الرسائل التلقائي (Webhooks)
لكي يستقبل الوكيل رسائل الزبائن ويرد عليها فوراً:
1. في لوحة مطوري فيسبوك (Developers Dashboard) تحت **Messenger** > **Webhooks**:
   - **Callback URL**: رابط السيرفر الخاص بك متبوعاً بـ `/webhooks/meta` (إذا كنت تشغل محلياً استخدم ngrok مثلاً: `https://your-domain.ngrok-free.app/webhooks/meta`).
   - **Verify Token**: اكتب: `hudhud_radar_secret_verify_token_2026` (الموجود في ملف `.env`).
2. اشترك في أحداث: `messages`, `messaging_postbacks`.

---

## 💎 تحويل التوكن إلى "توكن دائم مدى الحياة" (Never Expire Token)
افتراضياً يعطي فيسبوك توكن مؤقت ينتهي بعد 60 يوماً. لجعل التوكن دائم مدى الحياة:
1. احصل على **`App Secret`** من: **App settings** ⬅️ **Basic** ⬅️ اضغط **Show** بجانب **App secret**.
2. يقوم النظام برمجياً عبر الـ API بالآتي:
   - استبدال التوكن بتوكن طويل الأجل عبر `oauth/access_token?grant_type=fb_exchange_token`.
   - استخراج توكن الصفحة الدائم عبر `GET /{page_id}?fields=access_token`.
3. التوكن الناتج يمتلك خاصية `expires_at: 0` الرسمية في Meta، مما يعني أنه **لا ينتهي إطلاقاً** ولا يحتاج لتجديد ما لم تقم بتغيير كلمة سر الحساب.


# 📄 الوثيقة رقم 009: بروتوكول الربط المباشر لحسابات Meta وتوليد التوكن الدائم (Never Expire)
#archive #meta-api #permanent-token #facebook #instagram #security

- **رقم الوثيقة في الأرشيف**: `009`
- **التاريخ والوقت**: `2026-09-04 09:45:00 UTC+3`
- **الحالة**: منجز ومعتمد في النظام بنسبة 100% (Production Ready)
- **المنصات المعنية**: Facebook Page + Instagram Professional/Creator Account

---

## 🎯 الغرض من الوثيقة
توثيق الإنجاز المحوري في جعل وكيل **HudhudRadar** متصلاً بحسابات Meta الحقيقية دون انقطاع، وشرح الخوارزمية البرمجية الدقيقة التي تم بها تجاوز مشكلة انتهاء التوكن المؤقت (Short-lived Token) وتحويله إلى **Page Access Token دائم مدى الحياة (`expires_at = 0`)**.

---

## 📊 البيانات والحسابات المتصلة رسمياً

| البيان | القيمة الحقيقية في Meta | الحالة |
|---|---|:---:|
| **اسم تطبيق Meta** | `HudhudRadar AI` | نشط ومفعل |
| **معرف التطبيق (App ID)** | `2092880431308591` | موثق في `.env` |
| **سر التطبيق (App Secret)** | `1ddbef5f0c9292a82fd5f2382afdbb65` | مشفر ومحمي في `.env` |
| **اسم صفحة فيسبوك** | `إبدأ ماركتينج - Karim Abdalwahid` | متصلة |
| **معرف الصفحة (Page ID)** | `1108892288983475` | موثق في `.env` |
| **حساب إنستغرام** | `@karim__abdalwahid` | متصل |
| **معرف إنستغرام (IG ID)** | `17841459820747642` | موثق في `.env` |
| **نوع حساب إنستغرام** | `MEDIA_CREATOR` (صانع محتوى محترف) | متوافق 100% |

---

## 🔑 الصلاحيات الممنوحة رسمياً (Active Scopes)
تم فحص التوكن عبر Graph API Debugger وأكدت النتائج منح الصلاحيات التالية:
1. `pages_messaging`: للرد التلقائي على رسائل فيسبوك ماسنجر وإدارتها.
2. `instagram_manage_messages`: لإرسال واستقبال رسائل الـ DM على إنستغرام.
3. `instagram_manage_comments`: لقراءة والرد على تعليقات الريلز والمنشورات.
4. `instagram_basic`: لقراءة الملف الشخصي والميديا وإحصائيات الحساب.
5. `pages_read_engagement`: لمتابعة التفاعل وقراءة بيانات الصفحة.
6. `pages_show_list`: للتحقق من الصفحات التابعة للمستخدم.
7. `public_profile`: للتحقق من هوية المدير.

---

## ⚙️ الخوارزمية البرمجية لتحويل التوكن إلى "دائم" (Never Expire)

فيسبوك يعطي افتراضياً توكن مستخدم مؤقت ينتهي بعد ساعة أو ساعتين. لتحويله إلى توكن صفحة دائم لا ينتهي أبداً، تم تطبيق هذا البروتوكول:

### الخطوة 1: استبدال التوكن المؤقت بتوكن مستخدم طويل الأجل (60 يوماً)
```http
GET https://graph.facebook.com/v21.0/oauth/access_token?
    grant_type=fb_exchange_token&
    client_id={META_APP_ID}&
    client_secret={META_APP_SECRET}&
    fb_exchange_token={SHORT_LIVED_USER_TOKEN}
```
* **النتيجة**: توليد `long_lived_user_token` بصلاحية 60 يوماً (`expires_in = 5184000`).

### الخطوة 2: اشتقاق توكن الصفحة الدائم (Permanent Page Token)
```http
GET https://graph.facebook.com/v21.0/{PAGE_ID}?
    fields=access_token,name&
    access_token={LONG_LIVED_USER_TOKEN}
```
* **النتيجة**: توليد `permanent_page_token` المخصص حصرياً لصفحة `إبدأ ماركتينج`.

### الخطوة 3: التحقق البرمجي التام (Debug Token)
عبر الاستعلام:
```http
GET https://graph.facebook.com/debug_token?
    input_token={PERMANENT_PAGE_TOKEN}&
    access_token={APP_ID}|{APP_SECRET}
```
* **النتيجة الرسمية الموثقة**:
```json
{
  "data": {
    "app_id": "2092880431308591",
    "type": "PAGE",
    "application": "HudhudRadar AI",
    "expires_at": 0,
    "is_valid": true,
    "profile_id": "1108892288983475"
  }
}
```
> **ملاحظة أمنية وقانونية**: القيمة `expires_at = 0` هي المعيار الرسمي المعتمد في Meta للدلالة على أن التوكن دائم مدى الحياة ولا يتطلب تجديداً إلا في حال تغيير كلمة سر الحساب أو إعادة تعيين الصلاحيات يدوياً.

---

## 📡 ربط الويب هوك المباشر (Webhooks Subscription)
تم تفعيل اشتراك الصفحة في أحداث الرسائل بنجاح:
```http
POST https://graph.facebook.com/v21.0/{PAGE_ID}/subscribed_apps?
    subscribed_fields=messages,messaging_postbacks&
    access_token={PERMANENT_PAGE_TOKEN}
```
* **الاستجابة**: `{"success": true}` ✅.

---

## 🔗 الروابط المرجعية ذات الصلة
- ذاكرة المشروع الدائمة: [`../../PROJECT_MEMORY.md`](file:///c:/Users/Dell/Desktop/$AI_TESTING/HudhudRadar/PROJECT_MEMORY.md)
- إجراءات التكامل مع Meta: [`../PROJECT_BRAIN/SOPs/SOP_04_Meta_API_Integration.md`](file:///c:/Users/Dell/Desktop/$AI_TESTING/HudhudRadar/PROJECT_BRAIN/SOPs/SOP_04_Meta_API_Integration.md)
- فهرس الأرشيف الشامل: [`000_ARCHIVE_CATALOG.md`](file:///c:/Users/Dell/Desktop/$AI_TESTING/HudhudRadar/PROJECT_ARCHIVE/000_ARCHIVE_CATALOG.md)

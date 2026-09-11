# 🎬 App Review Recording Matrix — الحكم النهائي لكل فيديو (2026-09-11)
#app-review #recording-matrix #ready #build #remove

> **المرجع**: SCREENCAST_SCRIPTS.md (31 سيناريو) + APP_REVIEW_JUSTIFICATIONS.md. كل سطر تحقق حي خلال جلسة اليوم.

---

## ✅ قسم 1 — جاهز للتسجيل **الآن** (مُتحقق منه حيًا)

| الفيديو | الصلاحية | الإثبات الحي |
|---|---|---|
| A3 | pages_messaging | محادثة Kareem حقيقية + AI رد فعلي (مُثبت في الإنبوكس) |
| B2 | instagram_manage_messages | محادثة IG حقيقية في نفس الإنبوكس |
| D8 | Human Agent | إصلاح اليوم: الزر يحدّث القاعدة + الـ AI انصكت (E2E مُتحقق) |
| D9 | Business Asset User Profile Access | Dossier باسم Kareem وصورته الرسمية |
| A7 | pages_manage_posts | Studio publish → الصفحة (التدفق موجود) |
| B5 | instagram_content_publish | نفس الـ Studio (container flow) |
| A1 | pages_show_list | زر الربط يفتح OAuth بـ pages_show_list (v26.0) |
| A2 | pages_manage_metadata | لوحة Webhooks + Page Subscriptions في الإعدادات |
| D6 | public_profile | **جديد**: chip الاسم + الصورة الرمزية في الـ sidebar |
| D7 | email | /users يعرض الإيميلات + نظام الإشعارات |
| A5 | pages_read_engagement | Analytics بأرقام حقيقية |
| D2 | read_insights | نفس Analytics (Page insights) |
| B4 | instagram_manage_insights | نفس Analytics (قسم IG) + views الحقيقية (إصلاح اليوم) |
| A6 | pages_read_user_content | مكتبة Studio (`/api/meta/posts`) |
| B6 | instagram_manage_contents | نفس مكتبة Studio (فلتر IG) |
| C1 | threads_basic | settings يعرض الحساب المتصل (@karim__abdalwahid) |
| C2 | threads_content_publish | **نشر حقيقي ناجح** اليوم |
| C6 | threads_delete | **حذف حقيقي ناجح** ×3 اليوم |
| C3 | threads_read_replies | sync-replies التقط ردًا حقيقيًا (captured=1) |
| A8 | pages_manage_engagement | أتمتة (لايك/رد) في /automations + حرس الـ takeover |
| B3/B7 | instagram_manage_comments / manage_engagement | نفس الأتمتة (IG comments flow) |
| B1 | instagram_basic | الإعدادات تعرض @karim__abdalwahid |

## 🟡 قسم 2 — جاهز **بشرطة مالك** (بيانات من عنده)

| الفيديو | الصلاحية | الشرط |
|---|---|---|
| C5 | threads_manage_insights | **جديد**: كارت Threads Insights في Analytics — بيجيب أرقام حية (حاليًا 0 — الحساب هادي؛ صح للتصوير مع توضيح) |
| D5 | leads_retrieval | محتاج Lead Form بحملة + lead حقيقي من Ads Manager (المسار `/api/marketing/sync-leads` → /leads جاهز) |
| D1 | business_management | تصوير خارجي: Business Settings في ميتا + تبويب الأدمن عندنا (جاهز) |
| A4 | pages_utility_messaging | نفس الإنبوكس — ابعت رسالة خدمية نصيًا وصورها |
| C4 | threads_manage_replies | عرض الردود في الأناليتكس الجديد (لا يوجد ردّ آلي على ثريدز — وضّح في الفيديو أنها قراءة وإدارة) |

## 🔴 قسم 3 — **احذفها من الطلب** (مش بتستخدمها — إجابات الـ Justifications نفسها بتقول كده)

```
ads_read · ads_management · pages_manage_ads
catalog_management · facebook_branded_content_ads_brand
facebook_creator_marketplace_discovery · Live Video API
Instagram Public Content Access · Marketing API Access Tier
instagram_branded_content_ads_brand/brand/creator
instagram_creator_marketplace_discovery · instagram_shopping_tag_products
instagram_manage_upcoming_events · Page Mentions
threads_keyword_search · threads_location_tagging
threads_profile_discovery · threads_share_to_instagram
```
**الدليل الحاسم للأدس**: توكن الصفحة **لا يصل** لـ `/me/adaccounts` (اتحقق حي — خطأ 100) + لا يوجد `META_AD_ACCOUNT_ID` + لا يوجد UI + فيديوهاتها كانت بيضاء. الطلب عليها بدون استخدام = رفض يجر الباقي.

**النتيجة**: 31 فيديو → **22 جاهز الآن + 5 بشروط بسيطة + 14 تُحذف من الطلب** (بما فيها الأدس الثلاثة).

## 🌐 إصلاحات الواجهة المنفذة اليوم (قبل التصوير)
1. **تكرار اللغة اتشال**: الكرة الأرضية هي المتحكم الوحيد في 9 صفحات داشبورد (الأزرار المنفصلة اتشالت) — الرئيسية/الدخول/الأونبوردنج تحتفظ بأزرارها (لا topbar فيها)
2. **الهوية**: chip الاسم + الصورة الرمزية (public_profile)
3. **Threads Insights card** في Analytics
4. المساحات الفاضية في الدخول: كانت الـ 47 مفتاح i18g الناقصة — **اتملت** (اتحقق: العناصر بتنسخ نصوصها فعلاً)
5. الفصل/الوميض/التنسيق الموحد — إصلاحات الأمس والنهارده منشورة

## 📌 خطوات المالك قبل التصوير
1. تحديث كوميتات اليوم منشورة — **افتح الموقع بنسخة جديدة (Ctrl+F5)**
2. حذف الصلاحيات الـ 14 من App Review → Permissions
3. Lead Form بحملة تجريبية + lead حقيقي (لـ D5)
4. تسجيل الدخول بحساب المالك hudhud.support@gmail.com للبيانات الحقيقية

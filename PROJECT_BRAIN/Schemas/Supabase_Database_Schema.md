# 💾 Supabase Database Schema Specification
#schema #supabase #postgresql #leads #messages

مواصفات جداول قاعدة بيانات Supabase الخاصة بنظام **HudhudRadar**.

---

## 📊 الجداول الأساسية

### 1. جدول العملاء المحتملين (`leads`)
يخزن البيانات المستخرجة بدقة من فيسبوك وإنستغرام ومصادر البيانات المعتمدة.

| الحقل | النوع | الوصف |
| :--- | :--- | :--- |
| `id` | UUID (PK) | المعرف الفريد للعميل (توليد تلقائي `gen_random_uuid()`) |
| `source` | VARCHAR(50) | مصدر العميل: `facebook`, `instagram`, `manual`, `other` |
| `full_name` | VARCHAR(255) | الاسم الكامل المتاح رسمياً |
| `username` | VARCHAR(255) | اسم المستخدم على المنصة (إن وجد) |
| `profile_url` | TEXT | رابط الملف الشخصي |
| `bio` | TEXT | النبذة التعريفية العامة |
| `location` | VARCHAR(255) | الموقع الجغرافي المتاح علناً |
| `contact_email` | VARCHAR(255) | البريد الإلكتروني المتوفر قانونياً ورسمياً |
| `contact_phone` | VARCHAR(50) | رقم الهاتف المتوفر قانونياً ورسمياً |
| `facebook_account_id`| VARCHAR(255) | معرف حساب فيسبوك (Page-Scoped ID أو User ID) |
| `instagram_account_id`| VARCHAR(255)| معرف حساب إنستغرام (IGSID أو Username) |
| `linked_account_id` | UUID (FK) | معرف الحساب الآخر المرتبط المؤكد بنفس الشخص (يشير إلى `leads.id`) |
| `data_provenance` | JSONB | تتبع مصدر كل معلومة، توقيت جمعها، وحالة التأكيد اليدوي |
| `created_at` | TIMESTAMPTZ | تاريخ ووقت إنشاء السجل |
| `updated_at` | TIMESTAMPTZ | تاريخ ووقت آخر تحديث للسجل |

---

### 2. جدول الرسائل والمحادثات (`messages`)
يخزن كل رسالة متبادلة مع العميل ويرتبط مباشرة بسجل العميل.

| الحقل | النوع | الوصف |
| :--- | :--- | :--- |
| `id` | UUID (PK) | المعرف الفريد للرسالة |
| `lead_id` | UUID (FK) | معرف العميل المرتبط (يشير إلى `leads.id` - `ON DELETE CASCADE`) |
| `platform` | VARCHAR(50) | المنصة: `facebook`, `instagram` |
| `platform_message_id`| VARCHAR(255)| معرف الرسالة على المنصة لمنع التكرار |
| `sender_type` | VARCHAR(50) | نوع المرسل: `lead`, `agent`, `admin` |
| `content` | TEXT | نص الرسالة |
| `metadata` | JSONB | تفاصيل إضافية (مرفقات، Message Tags، أوقات التسليم والقراءة) |
| `sent_at` | TIMESTAMPTZ | وقت إرسال الرسالة الفعلي |
| `created_at` | TIMESTAMPTZ | وقت تسجيل الرسالة في النظام |

---

### 3. جدول طابور المراجعة اليدوية للهويات (`identity_verification_queue`)
يخزن الحالات المشتبه بارتباطها التي تتطلب تدخلاً واعتماداً بشرياً صريحاً.

| الحقل | النوع | الوصف |
| :--- | :--- | :--- |
| `id` | UUID (PK) | المعرف الفريد للطلب |
| `primary_lead_id` | UUID (FK) | العميل الأول |
| `candidate_lead_id`| UUID (FK) | العميل المرشح للربط |
| `match_reason` | TEXT | سبب الاشتباه (تطابق أسماء، معلومات متقاربة) |
| `confidence_score` | DECIMAL(5,2)| نسبة الثقة المقدرة (0.00 إلى 1.00) |
| `status` | VARCHAR(50) | الحالة: `pending`, `approved`, `rejected` |
| `reviewed_by` | VARCHAR(255) | المشرف الذي راجع الحالة |
| `reviewed_at` | TIMESTAMPTZ | وقت المراجعة |
| `created_at` | TIMESTAMPTZ | وقت إنشاء الإشعار |

---

### 4. جدول سجل العمليات والأنشطة (`activity_logs`)
سجل تدقيق كامل لكل العمليات التي ينفذها النظام.

| الحقل | النوع | الوصف |
| :--- | :--- | :--- |
| `id` | UUID (PK) | المعرف الفريد للسجل |
| `action_type` | VARCHAR(100)| نوع العملية (`send_message`, `fetch_metrics`, `sync_leads`) |
| `platform` | VARCHAR(50) | `facebook`, `instagram`, `system` |
| `target_id` | VARCHAR(255) | المعرف المستهدف (ID العميل، المنشور، الرسالة) |
| `status` | VARCHAR(50) | حالة العملية: `success`, `failed`, `in_progress` |
| `error_reason` | TEXT | سبب الفشل بالتفصيل (في حال عدم النجاح) |
| `details` | JSONB | تفاصيل تقنية إضافية |
| `executed_at` | TIMESTAMPTZ | توقيت التنفيذ الفعلي |

---

### 5. جدول إحصاءات وأداء الصفحات (`page_performance_metrics`)
| الحقل | النوع | الوصف |
| :--- | :--- | :--- |
| `id` | UUID (PK) | المعرف الفريد |
| `platform` | VARCHAR(50) | `facebook`, `instagram` |
| `metric_date` | DATE | تاريخ القياس |
| `reach` | BIGINT | الوصول |
| `impressions` | BIGINT | مرات الظهور |
| `engagement_rate` | DECIMAL(6,3)| معدل التفاعل |
| `followers_count` | BIGINT | إجمالي المتابعين |
| `leads_captured` | INT | عدد العملاء المستقطبين في هذا اليوم |
| `metadata` | JSONB | تفاصيل إضافية من Meta Insights |

---

### 6. جدول منشورات المحتوى والجدولة (`content_posts`)
يخزن المنشورات، وسيناريوهات الريلز، وسلاسل الاستوري مع مواعيد الجدولة وحالات النشر.

| الحقل | النوع | الوصف |
| :--- | :--- | :--- |
| `id` | UUID (PK) | المعرف الفريد للمنشور (`gen_random_uuid()`) |
| `platform` | VARCHAR(50) | المنصة المستهدفة: `both`, `facebook`, `instagram` |
| `post_type` | VARCHAR(50) | نوع المحتوى: `post`, `reel`, `story` |
| `content_text` | TEXT | نص المنشور أو السيناريو أو الكابشن |
| `media_urls` | JSONB | مصفوفة روابط الصور أو الفيديوهات المرفقة |
| `status` | VARCHAR(50) | حالة المنشور: `draft`, `scheduled`, `publishing`, `published`, `failed` |
| `scheduled_for` | TIMESTAMPTZ | الموعد المحدد للجدولة والنشر التلقائي |
| `published_at` | TIMESTAMPTZ | موعد النشر الفعلي |
| `meta_post_id` | VARCHAR(255) | معرف المنشور العائد من فيسبوك أو إنستغرام |
| `creation_mode` | VARCHAR(50) | طريقة الإنشاء: `ai_generated` أو `manual` |
| `generation_prompt` | TEXT | الفكرة أو الموضوع الأصلي المستخدم في التوليد |
| `error_message` | TEXT | تفاصيل أي خطأ في حال فشل النشر |
| `performance_metrics`| JSONB | بيانات التفاعل والمشاهدات اللاحقة للمنشور |
| `created_at` | TIMESTAMPTZ | توقيت إنشاء السجل |
| `updated_at` | TIMESTAMPTZ | توقيت آخر تعديل |

---

## 🧩 platform_connections (Phase 9.7 — 2026-09-10)

اتصالات المنصة لكل مستخدم — كل عميل يربط حساباته هو، والتوكنات **مشفّرة** في قاعدة البيانات (Fernet مشتق من SECRET_KEY عبر `src/core/crypto.py`). **ليست مصدر صلاحية** — `user_entitlements` هي المصدر الوحيد (قاعدة Entitlement ≠ Capability).

| العمود | النوع | الوصف |
| :--- | :--- | :--- |
| `id` | UUID (PK) | معرف تلقائي |
| `user_id` | UUID (FK→users CASCADE) | المالك |
| `platform` | VARCHAR(30) | `facebook` / `instagram` / `threads` |
| `account_id` | VARCHAR(120) | معرف الحساب المتصل (page_id / ig id / threads id) |
| `account_name` | VARCHAR(160) | اسم مقروء (username / اسم الصفحة) |
| `access_token_encrypted` | TEXT | **مشفر** — لا نص صريح مطلقًا |
| `token_expires_at` | TIMESTAMPTZ | null = لا تنتهي (توكنات الصفحات) |
| `scopes` | TEXT[] | التصريحات الممنوحة فعليًا |
| `metadata` | JSONB | linked_ig_id / linked_ig_username (upsell) / platform_user_id |
| `status` | VARCHAR(20) | `active` / `revoked` / `expired` |
| `connected_at` / `created_at` / `updated_at` | TIMESTAMPTZ | قاعدة SOP-03 + trigger |

- UNIQUE(user_id, platform, account_id) · فهارس user_id و(user_id, platform, status) · RLS بنمط المنصة (service_role فقط، anon مقطوع).
- **Upsell الذهبي**: ربط فيسبوك يكتشف IG مربوط بالصفحة → metadata.linked_ig_username → بطاقة upsell مقفولة في الـ wizard حتى شراء entitlement:instagram.
- الخدمة: `src/modules/connections/service.py` (ConnectionService + assert_entitled fail-closed) · المسارات: `/api/connections/*` (overview / authorize / callback / disconnect).

---

### إعدادات التطبيق المحفوظة بالخادم (`app_settings`)

إعدادات تشغيل خاصة بالـbackend فقط، مثل بيانات الربط المتغيرة. لا يصل إليها المتصفح مباشرة؛ الوصول يتم عبر FastAPI باستخدام service role فقط.

| الحقل | النوع | الوصف |
| :--- | :--- | :--- |
| `key` | TEXT (PK) | اسم الإعداد الفريد، مثل `meta_credentials` |
| `value` | JSONB | القيمة المنظمة للإعداد |
| `updated_at` | TIMESTAMPTZ | وقت آخر حفظ |

سياسة الوصول: جداول التطبيق تعمل بـRLS، وصلاحيات `anon` و`authenticated` مسحوبة من Data API. يبقى مفتاح `service_role` على الخادم فقط ولا يُوضع في المتصفح أو متغير `NEXT_PUBLIC_`.

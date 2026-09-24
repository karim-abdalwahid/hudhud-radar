# 🔒 Security Model & Compliance — HudhudRadar
#security #compliance #meta-tos #privacy

يحدد هذا المستند المعايير الأمنية وقواعد الخصوصية الصارمة التي تحكم نظام **HudhudRadar**.

---

## 🛡️ المبادئ الأمنية الأساسية

### 1. إدارة الأسرار والمفاتيح (Secrets Management)
- منع كتابة أي رمز وصول (Access Token) أو مفتاح واجهة برمجة تطبيقات (API Key) داخل الكود المصدري إطلاقاً.
- جميع المفاتيح السرية (`META_APP_SECRET`, `META_ACCESS_TOKEN`, `SUPABASE_SERVICE_ROLE_KEY`, `LLM_API_KEY`) تُحمّل من المتغيرات البيئية عبر ملف `.env`.
- ملف `.env` محمي ويُدرج دوماً داخل `.gitignore`.

### 2. التحقق من التوقيع الرقمي للـ Webhooks
- كل طلب وارد من منصات Meta يتم التحقق من توقيعه الرقمي في ترويسة `X-Hub-Signature-256`.
- أي طلب لا يتطابق توقيعه مع `APP_SECRET` يتم رفضه فوراً بـ HTTP 401 Unauthorized.

### 3. أمن قاعدة البيانات (Supabase Row-Level Security)
- تفعيل RLS على جميع جداول النظام (`leads`, `messages`, `activity_logs`, `identity_verification_queue`).
- استخدام الـ Service Role فقط من الخادم الخلفي، مع عزل أي وصول عام.

### 4. حماية البيانات والخصوصية (Data Privacy & Zero Fabrication)
- احترام خصوصية المستخدمين وعدم استخراج أو طلب أي بيانات حساسة لا يحق للصفحة الوصول إليها.
- تتبع منشأ كل معلومة في حقل `data_provenance` (متى استخرجت، من أي مصدر، وهل تم اعتمادها آلياً أم يدوياً).
- منع دمج هويات العملاء تلقائياً في حال الشك، وإحالتها لطابور المراجعة اليدوية لحماية دقة البيانات.

### 5. مكافحة الرسائل غير المرغوبة (Anti-Spam & Rate Limits)
- تطبيق محددات معدل إرسال الرسائل (Max Requests per Minute) لمنع إيقاف الحساب من قبل خوارزميات مكافحة السبام في Meta.
- التحقق الصارم من قاعدة نافذة الـ 24 ساعة لرسائل Messenger و Instagram Direct.

---

## ملحق أمني — دفاع SaaS متعدد الطبقات (2026-09-16)

1. **ملكية قبل البيانات:** لا يكفي أن يكون webhook صحيح التوقيع؛ يجب أن يحل
   recipient account إلى owner واحد active قبل أي قراءة/كتابة/رد.
2. **توكنات العملاء:** لا تخزن كنص عام في `.env` أو `app_settings`. تخزن مشفرة
   في `platform_connections`، وتسترجع فقط عبر ConnectionService والـentitlement
   للحساب والمالك نفسيهما. أسرار التطبيق وحدها تبقى environment-only.
3. **RAG:** `user_id` مطلوب في البحث والـRPC؛ unscoped retrieval يعيد no context
   أو يرفض. هذا خط دفاع مستقل عن صحة كود route.
4. **قاعدة البيانات:** Data API backend-only؛ `anon` و`authenticated` لا يملكان
   grants لجداول التطبيق أو RPCs الحساسة. `service_role` على الخادم فقط ويتجاوز
   RLS، لذلك تظل فلاتر `user_id` وfail-closed في طبقة الخدمة إلزامية.
5. **القيود البنيوية:** ownership required للموارد العميلية، active external
   account لا يرتبط بأكثر من tenant، وmetric uniqueness tenant-aware. علاقات
   الحذف cascade-safe حتى لا تنشأ بيانات بلا مالك.
6. **التحقق المستمر:** regression tests للعزل + smoke test حي لمستأجرين عند
   توفر حسابات مصرح بها. لا يسجل token أو محتوى معرفة حساس في الأدلة.

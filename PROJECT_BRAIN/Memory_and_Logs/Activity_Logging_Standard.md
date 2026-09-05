# 📜 معايير تسجيل الأنشطة والعمليات (Activity Logging Standard)
#logging #audit #analytics #monitoring

يحدد هذا المستند معايير تسجيل كل نشاط، عملية، واستجابة ينفذها نظام **HudhudRadar**.

---

## 🎯 الأهداف
1. الشفافية المطلقة لكل قرار يتخذه الوكيل الذكي.
2. التحليل الدقيق لأسباب الفشل والنجاح (Root Cause Analysis).
3. إمكانية مراجعة العمليات وتوليد تقارير تنفيذ تفصيلية في أي وقت.

---

## 📋 الحقول الإلزامية لكل سجل عملية
عند تسجيل أي نشاط في جدول `activity_logs` وفي السجل النصي `ACTIVITY_EXECUTION_LOG.md`، يجب توثيق:
- **`timestamp`**: التوقيت الدقيق بالثواني والمنطقة الزمنية.
- **`action_type`**: نوع الإجراء (مثل: `send_dm`, `fetch_insights`, `resolve_identity`, `auto_reply`, `rate_limit_throttle`).
- **`platform`**: المنصة (`facebook`, `instagram`, `system`).
- **`target_id`**: الحساب أو الرسالة أو العميل المستهدف.
- **`status`**: حالة الإجراء (`success`, `failed`, `throttled`, `pending_human_review`).
- **`error_reason`**: إذا فشلت العملية، تحديد السبب الجذري بدقة (رمز الخطأ، نص الاستجابة من Meta، أو انتهاء نافذة المراسلة).
- **`details`**: حمولة البيانات أو المعاملات ذات الصلة (بدون تضمين أي أسرار أو مفاتيح).

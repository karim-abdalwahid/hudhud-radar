# 🏛️ System Architecture — HudhudRadar
#architecture #system-design #backend

نظام **HudhudRadar** مبني وفق نمط المعمارية الطبقية المعيارية (Modular Layered Architecture)، لضمان الفصل الواضح للمسؤوليات وسهولة الصيانة والإضافة.

---

## 📐 مخطط الطبقات والمكونات الرئيسية

```mermaid
graph TD
    subgraph External Platforms
        FB[Facebook Page API]
        IG[Instagram Graph API]
        SUPA[(Supabase PostgreSQL)]
    end

    subgraph HudhudRadar Core
        WH[Webhooks Handler / API]
        SEC[Rate Limiter & Policy Enforcer]
        EXT[Zero-Assumption Extractor]
        IDR[Identity Resolver & Review Queue]
        LDS[Leads & Messages Service]
        KB[Business Knowledge Base]
        AGT[AI Conversational Agent]
        ANL[Analytics & Root-Cause Engine]
        REP[Report Generator]
    end

    FB -->|Webhooks / DMs| WH
    IG -->|Webhooks / DMs| WH
    WH --> SEC
    SEC --> EXT
    EXT --> IDR
    IDR -->|Direct Match| LDS
    IDR -->|Uncertain Match| REV[Manual Verification Queue]
    LDS --> SUPA
    KB --> AGT
    AGT -->|Compliant Reply| FB
    AGT -->|Compliant Reply| IG
    LDS --> ANL
    ANL --> REP
```

---

## 🧩 المكونات التفصيلية:
1. **API & Webhook Router (`src/api/` & `src/main.py`)**:
   - استقبال أحداث Meta وتأكيد سلامة التوقيع الرقمي (`X-Hub-Signature-256`).
2. **Meta Client & Policy Enforcer (`src/meta_api/`)**:
   - الالتزام الصارم بمحددات الاستخدام (Rate Limiting) ونافذة الـ 24 ساعة للمراسلة.
3. **Data Extraction & Identity Resolution (`src/identity/`)**:
   - استخلاص الحقول المتاحة رسمياً فقط بدون اختلاق.
   - التحقق من الروابط بين حسابات فيسبوك وإنستغرام.
4. **Leads & Messages Engine (`src/leads/`)**:
   - تخزين العملاء المحتملين والرسائل في Supabase مع تتبع المنشأ الكامل (`data_provenance`).
5. **AI Agent & Knowledge Base (`src/agent/`)**:
   - قراءة المعرفة المعتمدة وتوليد ردود طبيعية وإنسانية تراعي قيود وسياسات المنصة.
6. **AI Content Studio & Scheduler (`src/content_studio/`, `src/agent/content_engine.py`, `src/agent/scheduler.py`)**:
   - توليد نصوص المنشورات وسيناريوهات الريلز وسلاسل الستوري وفق أطر تسويقية معتمدة (AIDA).
   - إدارة حالات المنشورات والجدولة التلقائية عبر عامل خلفية (`asyncio.Task`) يفحص المنشورات المستحقة دورياً كل 30 ثانية.
7. **Meta Publishing Engine (`src/meta_api/publishing.py`)**:
   - إدارة عمليات النشر عبر Meta Graph API لمنشورات فيسبوك وحاويات إنستغرام ثنائية المراحل (Reels, Stories, Posts).
8. **Analytics & Performance Engine (`src/analytics/` & `src/reporting/`)**:
   - تحليل النجاح، أسباب الفشل، إحصاءات الصفحة، ومعدلات التحويل.

---

## ملحق الحالة التشغيلية — SaaS tenant boundary (2026-09-16)

المخطط أعلاه يشرح الطبقات التاريخية. في الإنتاج متعدد العملاء، تسبق كل طبقة
بيانات خطوة ملكية إلزامية:

```text
Meta / Instagram / Threads event
  → signature verification
  → ConnectionService resolves recipient account to one active user_id
  → tenant-scoped lead/message/identity/RAG/content/automation service
  → exact tenant token + entitlement gate for outbound Graph call
  → tenant-scoped audit/metrics/reporting
```

- `platform_connections` و`ConnectionService` هما جسر الحساب الخارجي إلى
  المستأجر، وليس `.env` أو `app_settings` العام.
- الوحدات الفعلية المعنية تشمل `src/modules/webhooks/`،
  `src/modules/connections/service.py`، `src/agent/`، وطبقات CRM/content/
  analytics. أسماء المسارات الأقدم في الرسم لا تنشئ مسار وصول عاماً.
- لا يسمح التصميم برد آلي أو retrieval أو publish عند غياب owner/connection
  صالح. هذه حماية تجارية وأمنية، وليست مجرد تحسين لواجهة المستخدم.
- المرجع التفصيلي للجداول والعقود: [[SaaS_Tenant_Data_Contract]].


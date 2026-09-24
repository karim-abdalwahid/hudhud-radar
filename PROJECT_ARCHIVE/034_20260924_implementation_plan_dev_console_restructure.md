# Implementation Plan: Developer & System Core Console Reorganization

**Document ID**: `PROJECT_ARCHIVE/034_20260924_implementation_plan_dev_console_restructure.md`  
**Date**: 2026-09-24  
**Author**: Antigravity AI Agent  
**Status**: APPROVED BY OWNER — IN EXECUTION  

---

## 1. Executive Summary & Problem Definition

The owner identified that the current **Developer Console (`/settings`)** suffers from several architectural, organizational, and UX issues:
1. **Unnecessary Duplication**: Features like "Change Password" are user-account operations that already exist in My Account (`/account`). Its presence in the Dev Console is redundant and confusing.
2. **Mixing Tenant Actions with Developer Tooling**: Buttons like "Connect with Facebook & Select Page" and "Connect Threads Account" belong to tenant onboarding/account management (`/onboarding`, `/account`), not platform developer settings.
3. **Outdated Single-Tenant Residuals**: Manual page access token and page ID form fields are leftovers from Phase 1, prior to the multi-tenant encrypted OAuth database architecture.
4. **Fragmentation Across 5 Scattershot Tabs**: Meta, Threads, and Webhooks were separated into 3 disparate tabs despite all belonging to the Meta Developer Integration surface. AI Master Switch was exiled to an "Account & Security" tab instead of living alongside AI Providers.
5. **Missing Critical System Observability**: The Dev Console lacked live Webhook ping/monitoring, system health checks (Supabase latency, env var status), background scheduler/cron execution controls, and platform subscription/pricing catalog controls.

---

## 2. Structural Architecture & Target Layout

The existing 5 tabs are restructured into **3 unified, professional, high-cohesion tabs**:

```
┌────────────────────────────────────────────────────────────────────────┐
│  Developer & System Core Console (Admin Only)                          │
├────────────────────────────────────────────────────────────────────────┤
│  [Tab 1: 🔌 Platform Integrations & Webhooks (تكاملات المنصات والويب هوك)]│
│  [Tab 2: 🧠 AI Engines & Master Control (محركات الذكاء ومفتاح الطوارئ)]│
│  [Tab 3: ⚙️ System Health & Scheduler (صحة الخوادم والمهام المجدولة)]    │
└────────────────────────────────────────────────────────────────────────┘
```

### Tab 1: 🔌 Platform Integrations & Webhooks
- **Meta & Threads Integration Diagnostics Card**:
  - Live Meta App ID, Configured status, Cloud Database connectivity.
  - Active Token Status & Page Diagnostics (read-only system overview).
- **Meta Developer Portal Setup Hub (One-Click Copy)**:
  - Consolidates every URL needed in the Facebook Developer Portal:
    - OAuth Redirect URI (`/api/connections/facebook/callback`)
    - Threads OAuth Callback URI (`/api/threads/oauth/callback`)
    - Threads Deauthorization / Uninstall Callback URL (`/api/threads/uninstall`)
    - Data Deletion Request URL (`/api/data-deletion`)
    - Webhook Callback URL (`/api/webhook/meta`)
    - Webhook Verify Token
    - Privacy Policy & Terms of Service URLs (`/privacy`, `/terms`)
- **Webhook Subscriptions & Policy Enforcement**:
  - Subscribed Webhook Fields: `messages, messaging_postbacks, feed, mention`
  - HMAC SHA-256 Signature Verification: Active & Enforced (`X-Hub-Signature-256`)
  - Meta 24h Messaging Window Policy: Strict Enforcement
  - Webhook Health Ping button (instant diagnostic check)

### Tab 2: 🧠 AI Engines & Master Control
- **Global AI Master Switch**:
  - Platform-wide emergency kill switch (`global_paused`) with active badge and toggle.
  - Clear scope indication (global vs tenant).
- **AI Providers Management (Google AI, Anthropic, OpenAI, OpenRouter, Custom)**:
  - Add Provider modal / form with live discovery and API key masking.
  - Provider Cards with enabled models count, sync status, and delete.
  - Manage Models modal to toggle availability for customers.
- **AI Telemetry & Daily Usage Summary**:
  - Live KPIs from `/api/admin/overview`: Today's AI calls and operations count.

### Tab 3: ⚙️ System Health & Scheduler
- **System Health Matrix**:
  - Supabase Database Status & Latency check.
  - Auth Session Engine & Security Token validation status.
  - Environment Configuration Check (safe boolean verification of required secrets).
- **Background Cron Jobs & Schedulers**:
  - Threads Token Auto-Refresh Job (`/api/cron/threads-token-refresh`).
  - Polar Subscription Reconciliation Job (`/api/admin/billing/reconcile`).
  - Content Scheduler Tick (`/api/cron/scheduler-tick`).
  - Insights Sync Job (`/api/cron/insights-sync`).
  - "Run Now" (تشغيل الآن) manual triggers for admin testing with toast feedback.
- **Platform Pricing & Addon Catalog**:
  - Admin view of platform prices (`/api/admin/billing/catalog`).
  - Multi-platform discounts and trial days configuration (`/api/admin/billing/settings`).

---

## 3. Removals
- **REMOVED**: "Change Password" form (retained only in `/account`).
- **REMOVED**: "Connect with Facebook & Select Page" SDK flow from Dev Console (managed in `/account` and `/onboarding`).
- **REMOVED**: "Connect Threads Account" button from Dev Console (managed in `/account`).
- **REMOVED**: Manual page access token input forms from Dev Console.

---

## 4. Verification & Testing
1. Unit Tests: Ensure all 382 pytest tests pass without regression.
2. Endpoint Verification: Verify all admin endpoints (`/api/meta/status`, `/api/ai/providers`, `/api/admin/overview`, `/api/admin/billing/catalog`, `/api/admin/billing/settings`, `/api/admin/alerts`) respond with HTTP 200 and expected contracts.
3. UI Testing: Dark mode contrast, responsive layouts, RTL/LTR i18n label parity, `hudhudToast` feedback for copy actions and switches.

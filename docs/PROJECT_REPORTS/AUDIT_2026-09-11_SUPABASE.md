# 🗄️ Supabase Deep Audit — 2026-09-11

## 1. Tables & RLS

| Table | RLS Enabled | Policies |
|---|---|---|
| activity_logs | ✅ | 1 |
| ai_models | ✅ | 1 |
| ai_providers | ✅ | 1 |
| app_settings | ✅ | 1 |
| campaigns | ✅ | 1 |
| content_posts | ✅ | 1 |
| coupon_redemptions | ✅ | 1 |
| coupons | ✅ | 1 |
| identity_verification_queue | ✅ | 1 |
| kb_chunks | ✅ | 1 |
| kb_documents | ✅ | 1 |
| leads | ✅ | 1 |
| message_templates | ✅ | 1 |
| messages | ✅ | 1 |
| notifications | ✅ | 1 |
| page_performance_metrics | ✅ | 1 |
| payment_events | ✅ | 1 |
| platform_addons_catalog | ✅ | 1 |
| platform_connections | ✅ | 1 |
| processed_events | ✅ | 1 |
| site_traffic | ✅ | 1 |
| usage_events | ✅ | 1 |
| user_entitlements | ✅ | 1 |
| user_subscriptions | ✅ | 1 |
| users | ✅ | 1 |

✅ All tables have RLS enabled.

## 2. Per-user isolation columns (user_id)

| Table | has user_id |
|---|---|
| leads | ✅ |
| messages | ✅ |
| content_posts | ✅ |
| notifications | ✅ |
| activity_logs | ✅ |
| page_performance_metrics | ✅ |
| kb_documents | ✅ |
| platform_connections | ✅ |
| user_subscriptions | ✅ |
| user_entitlements | ✅ |
| automations_workflows | ❌ MISSING |

## 3. Foreign key relationships

| From | Column | → To |
|---|---|---|
| activity_logs | user_id | users |
| ai_models | provider_id | ai_providers |
| content_posts | user_id | users |
| coupon_redemptions | user_id | users |
| coupon_redemptions | coupon_id | coupons |
| coupons | applies_to_user | users |
| identity_verification_queue | candidate_lead_id | leads |
| identity_verification_queue | primary_lead_id | leads |
| kb_chunks | document_id | kb_documents |
| kb_documents | user_id | users |
| leads | user_id | users |
| leads | linked_account_id | leads |
| messages | user_id | users |
| messages | lead_id | leads |
| notifications | user_id | users |
| page_performance_metrics | user_id | users |
| payment_events | user_id | users |
| platform_connections | user_id | users |
| site_traffic | user_id | users |
| usage_events | user_id | users |
| user_entitlements | user_id | users |
| user_subscriptions | user_id | users |

## 4. Data distribution per user (non-null user_id counts)

- **leads**: [] | NULL user_id rows: 2
- **messages**: [] | NULL user_id rows: 5
- **content_posts**: [] | NULL user_id rows: 64
- **kb_documents**: [] | NULL user_id rows: 0
- **platform_connections**: [] | NULL user_id rows: 0
- **user_subscriptions**: [] | NULL user_id rows: 0
- **user_entitlements**: [] | NULL user_id rows: 0

## 5. Policy names sample (per table)

| Table | Policy | Cmd |
|---|---|---|
| activity_logs | Allow all access to service_role | ALL |
| ai_models | Allow all access to service_role | ALL |
| ai_providers | Allow all access to service_role | ALL |
| app_settings | Allow all access to service_role | ALL |
| campaigns | Allow all access to service_role | ALL |
| content_posts | Allow all access to service_role | ALL |
| coupon_redemptions | Service role full access on coupon_redemptions | ALL |
| coupons | Service role full access on coupons | ALL |
| identity_verification_queue | Allow all access to service_role | ALL |
| kb_chunks | Allow all access to service_role | ALL |
| kb_documents | Allow all access to service_role | ALL |
| leads | Allow all access to service_role | ALL |
| message_templates | Service role full access on message_templates | ALL |
| messages | Allow all access to service_role | ALL |
| notifications | Service role full access on notifications | ALL |
| page_performance_metrics | Allow all access to service_role | ALL |
| payment_events | Service role full access on payment_events | ALL |
| platform_addons_catalog | Service role full access on platform_addons_catalog | ALL |
| platform_connections | Service role full access on platform_connections | ALL |
| processed_events | Allow all access to service_role | ALL |
| site_traffic | Service role full access on site_traffic | ALL |
| usage_events | Service role full access on usage_events | ALL |
| user_entitlements | Service role full access on user_entitlements | ALL |
| user_subscriptions | Service role full access on user_subscriptions | ALL |
| users | Allow all access to service_role | ALL |
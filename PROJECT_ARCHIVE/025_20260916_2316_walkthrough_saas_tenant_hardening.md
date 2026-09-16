# Walkthrough 025 — SaaS Tenant Hardening and Approved Legacy Cleanup
#archive #walkthrough #supabase #tenant-isolation #2026-09-16

**Timestamp:** 2026-09-16T23:16:51+03:00  
**Owner approval:** The owner approved implementation, GitHub upload, and deletion of every historical row with no tenant owner.  
**Repository:** `karim-abdalwahid/hudhud-radar`, `main`  
**Release commit:** `d32d9bc fix: enforce tenant isolation across SaaS data flows`

## Objective

Make the product match the intended SaaS contract: every customer owns their connected social accounts, CRM, uploaded knowledge, automations, content, analytics, and outbound actions. No inbound event, RAG query, read, write, credential, or dedup key may fall back to another tenant or a shared workspace.

## Findings that drove the work

1. The real inbound AI reply path possessed `lead_data.user_id` but did not forward it into RAG/sales context.
2. Several product paths still assumed a global workspace or shared credential/cache.
3. Legacy RLS policies and grants could allow browser roles to access backend data directly.
4. Nullable ownership and global metric/account uniqueness could permit a programming error to become cross-tenant state.

## Delivered design

- Exact account → tenant resolution and entitlement-gated encrypted credentials through `ConnectionService`.
- Owner propagation through Meta/Instagram/Threads inbound processing, CRM, conversation/RAG, comment and reply bridges, marketing imports, scheduler/publisher, and analytics/reports.
- Fail-closed service-layer guards where an omitted owner could otherwise query global data.
- Scoped event/message idempotency.
- Legacy global Meta/Threads/automations/cache storage removed from production paths.
- Database migration `20260916190000_harden_backend_and_remove_unowned_legacy_data.sql`:
  - removes approved ownerless legacy data and global settings;
  - adds `campaigns.user_id`, tenant metric uniqueness, and globally unique active external accounts;
  - makes customer ownership mandatory;
  - fixes cascade-safe foreign keys;
  - turns the public Data API into a service-role-only backend interface.

## Live safety evidence

Preflight found no duplicate active external account and no campaign needing backfill. The approved cleanup removed:

- 11 messages; 3 leads; 75 content posts; 21 metrics; 185 activity logs;
- 11,957 anonymous traffic rows; 7 global dedup rows;
- 4 shared settings keys.

No KB documents, payment events, notifications, or automation workflows without owners existed.

After `npx supabase db push --linked` completed successfully:

- every affected `user_id IS NULL` count was zero;
- no shared legacy settings remained;
- unauthenticated Data API access to `leads` was blocked with HTTP 401.

## Verification and release

- `python -m compileall -q src` passed.
- `git diff --check` passed (Windows CRLF notices only).
- Full test suite: **320 passed, 2 skipped**; skips require an unavailable Threads app-id test setting.
- Pushed to the approved remote only: `origin/main` → commit `d32d9bc`.

## Follow-up

Rotate Meta and Threads credentials/tokens that previously lived in the retired shared credential shape. Preserve this document and the linked session/memory record as the exact historical context for future changes.

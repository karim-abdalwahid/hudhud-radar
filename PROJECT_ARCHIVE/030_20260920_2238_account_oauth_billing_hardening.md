# Account, OAuth, and Trial Billing Hardening

**Recorded:** 2026-09-20T22:38:17+03:00
**Status:** Implemented and verified locally; production payment configuration still needs an external smoke test.

## Why this work started

The owner asked Codex to independently verify an external audit and three supplied account-page artifacts, then immediately repair only the findings that fit HudhudRadar's tenant-safe SaaS design. The owner had already selected a separate customer Account page and confirmed the platform is pre-launch.

## Verified findings and corrections

| Finding | Verdict | Result |
|---|---|---|
| A normal customer had no Account surface for subscription, connections, AI pause, password, and sign-out. | Confirmed | Added tenant-scoped `/account`. |
| OAuth callbacks sent users to admin Settings. | Confirmed | Facebook, Instagram, and Threads now return to Account. |
| Instagram callback required signed state but authorize did not send it. | Confirmed additional defect | Added signed state to the authorization request. |
| Trial could be reused. | Confirmed | Durable trial marker blocks new checkout and service re-entry. |
| Trial was already correctly granted by webhook. | Not confirmed | Repaired webhook handling so verified trial events now create entitlements. |
| Analytics was admin-only despite owner-scoped APIs. | Confirmed | Made customer page reachable without granting admin access. |

## Security and product implementation

- The Account page fetches session-bound data and renders it with `textContent`, `replaceChildren`, and event listeners. It does not inject an account name into inline JavaScript, avoiding the unsafe supplied-patch pattern.
- Threads authorization checks `user_entitlements`; disconnect treats a failed backend response as failure rather than showing false success.
- Onboarding starts trial checkout with `POST /api/billing/trial` and follows the returned checkout URL. It no longer pretends a checkout succeeded merely by navigating to a success page.
- Trial product mappings must exist. The application fails explicitly instead of silently substituting a paid product. Trial to paid conversion refreshes entitlement source and expiry.
- All customer-facing trial copy and Terms now match the application model: **three days**, not fourteen.

## Evidence

- Complete test suite: **339 passed, 2 skipped, 1 warning**.
- `python -m compileall -q src` passed.
- `git diff --check` passed.
- The two skips require a local `THREADS_APP_ID`; the warning is a dependency deprecation, not a test failure.
- A disposable audit probe used only to inspect webhook routing was deleted immediately. No customer records were read, changed, or retained.

## Release boundary and next steps

Supabase contains the expected trial product mappings, but no Polar access token is available in the local runtime. No credential was printed, invented, or modified. Before launch, confirm the secret and the three-day trial product configuration in the actual Vercel/Polar environment, then run a real checkout and webhook smoke test.

Do not implement cancellation by assumption. The owner must choose whether a cancellation ends at the paid period or revokes access immediately, including the desired Polar customer-portal/trial behavior. Usage-event metering, credit enforcement, persona runtime, and provider selection remain separately governed Phase 9.4 work.

## Scope preservation

The supplied untracked `account/` directory was deliberately left untouched, and no other repository or unrelated local work was changed.

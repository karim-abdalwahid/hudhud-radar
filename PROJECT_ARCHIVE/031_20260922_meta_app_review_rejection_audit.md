# Meta App Review Rejection Audit and Resubmission Plan

**Recorded:** 2026-09-22
**Type:** Read-only product, permission, and evidence audit.

## Decision

The App Review rejection does not generally prohibit HudhudRadar's social-sales
model. Meta's feedback says the submitted screencasts did not show the required
end-to-end proof: Meta consent, the visible Hudhud action, and the corresponding
native Meta result. `instagram_manage_contents` is the explicit exception; Meta
judged it invalid or unnecessary for the core use case shown.

## Important corrections to prior review material

- Hudhud has no Meta utility/marketing template lifecycle, so its internal
  lifecycle templates cannot justify `pages_utility_messaging`.
- The historical Page/Instagram content import and Meta-to-KB sync paths return
  explicit unavailable responses to preserve tenant isolation. They cannot
  honestly justify `pages_read_user_content` or `instagram_manage_contents`.
- Threads mentions are not requested by the Threads OAuth scope; historical
  notes confused Facebook Page webhook mentions with a Threads capability.
- A backend Threads reply route does not constitute a customer-visible workflow
  while Studio has no reply composer.
- `Human Agent` and comment-engagement flows need policy/scope alignment before
  recording, not a simulated demonstration.

## Deliverable

`docs/APP_REVIEW/2026-09-22_META_RESUBMISSION_PLAN.md` contains the full
permission matrix, exact page locations, preconditions, owner checklist, and a
browser-agent prompt that requires real test assets and forbids fabricated proof.

## Scope

No code, App Review request, Meta configuration, production data, credential, or
deployment was modified. The owner must remove unsupported requests and prepare
real test assets before resubmission.

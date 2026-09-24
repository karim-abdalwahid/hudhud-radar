# Meta App Review — Verified Resubmission Plan

**Recorded:** 2026-09-22 · **Updated:** 2026-09-24 (live verification of the messaging blocker)
**Status:** Audit and recording plan only. No permission, production setting, or application code was changed.

## 2026-09-24 verification addendum — messaging is the only live gate

A live production read-only probe (`diag_ig_dm.py`) confirmed the exact current state:

| Probe (live, production) | Result | Meaning |
|---|---|---|
| `GET /{IG_ID}/subscribed_apps` | 400, field `subscribed_apps` not exposed | IG webhook subscription is not reflectable — consistent with capability gating |
| `GET /{IG_ID}/conversations` | 400 **error #3** "Application does not have the capability" | **The blocker is live today:** `instagram_manage_messages` Advanced Access is still not granted |
| `processed_events` (webhook) | All recent events are `[message]` Facebook only | No real IG DM has ever been delivered to the webhook |
| Signed `object=instagram` simulation | Lead `src=instagram` + message stored in production (2026-09-24T13:00Z) | Site-side webhook→lead→message path is fully functional |

Actions confirmed with the owner (2026-09-24): keep the existing plan below as the 
recording script, and re-confirm **only** the permissions actually demonstrated once
Advanced Access for `instagram_manage_messages` is granted. The AI auto-reply path
(`src/agent/orchestrator.py`) is code-complete for Instagram; it is not reachable
for real DMs until Meta grants the subscription capability.

The verified degraded path fix (honest failure reporting, no silent fake success)
was shipped separately in this same session: when Meta rejects a send, the
orchestrator now returns `reply_sent: None` + `reply_error` instead of claiming
the reply was delivered.

## Bottom line

Meta did **not** say that HudhudRadar's social-sales use case is forbidden. For nearly every rejected item, the reviewer said the screencast did not show the complete path: a user logs in, grants the relevant Meta access, uses the feature in Hudhud, and sees the resulting action/data in the native Meta product. The two explicit reviewer notes require a real in-app send and native delivery for messaging, and real template selection, variable population, send, and native delivery for utility messaging.

The old App Review recording documents are historical and overstate some paths. This plan is based on the current tenant-safe runtime, not an old global-token implementation.

## Do not resubmit these now

| Permission / feature | Verified current state | Decision |
|---|---|---|
| `pages_utility_messaging` | Hudhud has no Meta utility/marketing-template integration. `/templates` is an internal admin lifecycle-template screen, not Meta template creation/selection or placeholder delivery. | **Remove now.** Do not fake a template video. Build a real template workflow first if this becomes a product need. |
| `pages_read_user_content` | The historical per-account content/KB sync is explicitly disabled with HTTP 409 to protect tenant isolation. | **Remove/hold.** Re-request only after a tenant-scoped import shows real Page posts/comments in the user's workspace. |
| `instagram_manage_contents` | The matching live-content endpoint is disabled for the same tenant-safety reason; Meta explicitly called this request non-core. | **Remove.** Basic/profile/media access used by the supported connection path is enough for current features. |
| `instagram_manage_insights` | Current direct-Instagram OAuth requests `instagram_business_manage_insights`, not this legacy variant. | **Remove.** Use the business permission only where the direct-Instagram path is demonstrated. |
| `threads_manage_mentions` | No Threads OAuth scope requests it; current `mention` code is for Facebook Page webhooks and is incorrectly labelled in old notes. | **Remove.** It is not a live Threads feature. |
| `threads_manage_replies` | A protected backend endpoint exists, but no customer-facing Threads reply composer exists in Studio. | **Hold/remove now.** Re-request only after a user can compose, send, and see a Threads reply from the visible UI. |

## Re-request only after the listed precondition

| Permission / feature | Why the product needs it | Precondition before recording/submission |
|---|---|---|
| `Human Agent` | A real business owner can take over a Messenger/Instagram conversation and manually support a customer while AI is paused. | Tighten the live policy path first: apply HUMAN_AGENT only to an owner-written human reply in the permitted time window, record it as human rather than AI, and never use it for automated or promotional content. |
| `pages_manage_engagement` | The automation engine can like and publicly reply to comments on the owner's Page. | Add it to the Facebook OAuth scope set, then use a real test comment and show the native Page result. |
| `instagram_manage_engagement` | The automation engine can like and publicly reply to comments on the owner's Instagram. | Align the exact OAuth scope used by the supported Instagram connection, then show a real test comment and native Instagram result. |

## Permissions that match a visible current product feature

Already approved items (`pages_show_list`, `pages_manage_metadata`, `pages_read_engagement`, `business_management`, `public_profile`, `email`, `leads_retrieval`, and Business Asset User Profile Access) do **not** need a new request unless Meta asks for one.

| Permission(s) | Current visible location | Exact evidence required in recording |
|---|---|---|
| `pages_messaging` | `/inbox` | Select the connected Page conversation, manually type a support reply in Live Inbox, click **Send**, then show that exact text in Messenger. |
| `pages_manage_posts` | `/studio` | Create a Page post, publish it, then refresh the Facebook Page and show the same text/media. |
| `read_insights` | `/analytics` | Click **Refresh Metrics** and show Page metrics associated with the selected connected Page. |
| `instagram_basic` / `instagram_business_basic` | `/account` after connection; onboarding connection step | Show the customer choosing and authorizing their own professional account, then show its account name in Account. |
| `instagram_manage_messages` / `instagram_business_manage_messages` | `/inbox` | Send a manual support reply to an inbound Instagram DM, then show the same message in Instagram native inbox. |
| `instagram_content_publish` / `instagram_business_content_publish` | `/studio` | Create/publish one post or Reel and show it on the native Instagram profile. |
| `instagram_manage_comments` / `instagram_business_manage_comments` | `/automations` | Create/activate a comment rule, post a real test comment, and show the public reply (and like only if enabled) on Instagram. |
| `instagram_business_manage_insights` | `/analytics` | Refresh and show Instagram reach/views/follower metrics for the connected professional account. |
| `threads_basic` | `/account` | Click **Connect Threads**, complete Threads OAuth, then show the connected username/status. |
| `threads_content_publish` | `/studio` | Publish a test Thread and show it in native Threads. |
| `threads_delete` | `/studio` | From **My Threads**, delete the test post and refresh native Threads to show it is gone. |
| `threads_read_replies` | `/studio` | Reply from a second test Threads account, open **Replies** for that exact Thread, and show the same reply in Hudhud. |
| `threads_manage_insights` | `/analytics` | Refresh the Threads Insights card and show its values for the connected account. |

## Non-negotiable recording setup

1. Use a clean **English** Hudhud UI and English captions/tooltips. Record at readable resolution, normal speed, without cuts that hide a step.
2. Use only test assets you own: one Facebook Page, one Instagram Professional account, one Threads account, and a second test Messenger/Instagram/Threads account for inbound messages/comments/replies. Never show a real customer's identity or secret.
3. Start each video logged out of the relevant Hudhud connection. Show the Hudhud sign-in, click the connection action, complete the Meta OAuth consent screen where the requested access is granted, then return to Hudhud.
4. Each action must visibly succeed in both places: Hudhud and the native Meta client/site. A dashboard card, API log, or a simulated alert alone is not proof.
5. Narrate or caption the precise permission and why the owner benefits. Do not claim the AI sends a `Human Agent` message or that a generic Hudhud template is a Meta utility template.

## Which account records the review

Record the product flow with a **normal Hudhud user**, not the Hudhud admin.
The normal user must own the test social assets and must have the needed test
entitlement (Facebook, Instagram, or Threads). In pre-approval development,
that same person's Meta identity may be an App Tester/Developer so it can grant
the app access; this is separate from being a Hudhud administrator.

The Hudhud admin may prepare the test user, test entitlement, and test assets
off-camera. Then log out and record the actual customer journey with the normal
user. Admin bypasses parts of the entitlement path and exposes admin-only
screens, so it is weaker evidence of the SaaS customer experience.

## Current user-readiness truth table

| Flow | Normal user status | Recording condition / known gap |
|---|---|---|
| Account, onboarding, Inbox, Studio, Automations | Available as tenant-scoped user surfaces | Use the ordinary user who owns the test data and platform connection. |
| Facebook / Instagram connection | Available | The ordinary user needs the matching entitlement; Meta app/tester configuration and the app credentials must be live. |
| Threads connection, publishing, deletion, reply reading, insights | Available | The ordinary user needs the Threads entitlement and a configured Threads app. |
| Analytics | Direct page/API access is user-scoped | Current sidebar JavaScript still treats `/analytics` as a developer route and hides its link for ordinary users. Open `/analytics` directly until that UI drift is fixed. |
| Page/Instagram content import into KB | Not available | Tenant-safe legacy sync deliberately returns HTTP 409. Do not record/request those permissions. |
| Meta utility templates | Not available | Internal notification templates are not Meta templates. |
| Threads reply composition / mentions | Not available as visible user workflows | Hold the related permissions until UI/product work exists. |
| Human Agent | UI exists but not submission-ready | Current manual-send path applies the Human Agent tag broadly and stores the message as agent-sent. Narrow and label it as a genuine human-only policy path before requesting it. |
| Page/Instagram engagement automation | Feature code and Automations UI exist | Add/align the corresponding OAuth scopes and verify a real native comment action before recording. |

## Browser-agent master prompt

Give the following prompt to the recording agent **after** you have supplied a logged-in browser profile for the test assets. The agent must stop and report a blocker if an expected real result does not appear; it must not fabricate proof.

```text
Record Meta App Review screencasts for HudhudRadar. This is evidence, not a marketing demo. Use English UI. Work only with the owner's test Facebook Page, Instagram Professional account, Threads account, and second test customer accounts already logged in. Do not reveal passwords, tokens, app secrets, or real customer data.

For every requested permission, record one continuous end-to-end path:
1) sign in to Hudhud; 2) start the relevant Meta/Instagram/Threads connection from Hudhud; 3) show Meta OAuth consent granting the requested access; 4) return to Hudhud; 5) use the exact visible feature below; 6) open the native Meta app or website and show the same sent/published/retrieved result. Add short English on-screen captions naming the permission and explaining the button before it is clicked. Do not use cuts that conceal a step.

Record only these supported flows:
- pages_messaging: /inbox → select connected Page conversation → manually type a non-promotional support reply → Send → show identical delivery in Messenger.
- pages_manage_posts: /studio → create/publish a test Facebook post → show it on the connected Page in Facebook.
- read_insights: /analytics → Refresh Metrics → show Page metrics belonging to the connected Page.
- Instagram basic: /account → Connect Instagram (or onboarding connection step) → Meta consent → show the connected professional account name.
- Instagram messaging: /inbox → select an inbound Instagram DM → type/send a manual reply → show identical delivery in Instagram native inbox.
- Instagram publishing: /studio → create/publish a test post → show it on the connected Instagram profile.
- Instagram comments: /automations → create/activate a rule for a test keyword and visible public reply → send that keyword as a test comment from the second account → show the public reply in Instagram. Show a like only when the rule has it enabled.
- Instagram insights: /analytics → refresh → show metrics for the connected professional account.
- Threads basic: /account → Connect Threads → Threads OAuth consent → show connected username/status in Account.
- Threads publish/delete: /studio → publish test Thread → show it natively → use My Threads delete control → refresh native Threads and show it gone.
- Threads read replies: reply from the second test Threads account → /studio → open Replies for the exact Thread → show the same reply retrieved.
- Threads insights: /analytics → Refresh Threads Insights → show values for the connected Threads account.

Do NOT record or submit pages_utility_messaging, pages_read_user_content, instagram_manage_contents, instagram_manage_insights, threads_manage_mentions, or threads_manage_replies. They are not currently supported as visible, reviewable product flows. Do NOT record Human Agent until the owner confirms its policy-safe implementation is ready. When it is ready, show /inbox → Human Takeover Active / AI paused → a real human types a support response → send → same response in Messenger, with no AI-generated content.
```

## Owner checklist before resubmission

- Remove the six unsupported/duplicate requests above from App Review.
- Decide whether to implement the three conditional capabilities; do not submit them until their prerequisite is complete and a live test proves it.
- Prepare fresh OAuth consent for each recorded platform and the second test recipient account.
- Match every submission note word-for-word to the screen recording and to the actual feature. For messaging, explicitly state that the customer initiated the conversation; for Human Agent, state that only a real owner writes the reply.
- Upload the new videos with publicly accessible reviewer access and re-request only the permissions actually demonstrated.

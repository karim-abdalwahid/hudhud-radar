# 🎬 Meta App Review — Screencast Scripts (31 videos)
**Give this file to the recording model. Follow it EXACTLY.**

---

## ⚙️ UNIVERSAL RULES (apply to EVERY video)

1. **One take, zero editing/cuts.** Meta rejects edited clips.
2. **Always show the browser address bar** (full window recording, 1920×1080).
3. **Start every video from a clean state**: open `https://www.hudhd.com` first, then navigate.
4. **Site language = English** (default). Cursor visible and moves deliberately.
5. **Login used in videos**: `admin.test@hudhud.test` / `AdminTest#2026` — OR the owner's admin `hudhud.support@gmail.com` if the demo needs the owner's connected accounts (RECOMMENDED for messaging/publishing demos — real conversations needed).
6. **Show the result OUTSIDE our app too** when the script says so (open Messenger/Instagram/Threads in another tab and show the sent message/post live — reviewers love end-to-end proof).
7. **Narrate in English** (scripts provided below). Speak slowly and clearly.
8. **Duration**: 45–90 seconds each, unless noted.
9. **Recording tool**: Windows Game Bar (`Win + G`) or OBS. File name = the permission name (e.g., `pages_messaging.mp4`).

### Login procedure (shown at the start of videos that need it — keep it to 5 seconds):
> "This is Hudhud, our SaaS platform for managing Facebook, Instagram and Threads for our clients. I'm logged in with an admin account."
(If the video needs the login itself shown: type the email + password live.)

---

## 📘 GROUP A — Facebook / Messenger (page: إبدأ ماركتينج - Karim Abdalwahid)

### A1. `pages_show_list` — listing the user's Facebook Pages
1. Open `hudhd.com/settings` → Meta tab.
2. Show the connected Page card: **"إبدأ ماركتينج - Karim Abdalwahid"** with its Page ID.
3. Click **Connect with Facebook** → the Facebook OAuth popup opens **listing the user's Pages** to choose from.
4. Say: "When a client connects, Facebook shows them the list of Pages they manage through pages_show_list — here they select the Page Hudhud will operate."
5. Close the popup (don't complete re-connect), show the already-connected state.

**Narration**: "pages_show_list lets Hudhud list the Facebook Pages a client manages, so they pick which Page our AI agent operates."

### A2. `pages_manage_metadata` — subscribing the app to Page webhooks
1. Tab 1: `hudhd.com/settings` → Meta tab → Webhooks section (callback URL `https://www.hudhd.com/api/webhook/meta` + verified status).
2. Tab 2 (open it live): Meta developers dashboard → Messenger settings → Webhooks → show the same callback URL + verify token configured; open **Edit Page Subscriptions** → show `feed, messages, messaging_postbacks, messaging_referrals` checked → click Confirm.
3. Back to Tab 1: show our app's connection status "Connected ✓".

**Narration**: "pages_manage_metadata lets Hudhud subscribe the client's Page to our webhook — so every customer message reaches our AI agent in real time."

### A3. `pages_messaging` — receiving & replying to customer DMs (CORE — 90s)
1. Open `hudhd.com/inbox` → show a real customer conversation from Messenger.
2. Show the AI agent's reply already in the thread (point at it).
3. Click **Human Takeover** → type a short reply (e.g., "Hi! How can we help you today?") → **Send**.
4. Open Messenger (second tab or phone) → **show the exact message delivered** to the customer.
5. Say: "Customer messages arrive through Messenger webhooks; our AI replies automatically within the 24-hour window, and a human can take over anytime — all through pages_messaging."

### A4. `pages_utility_messaging` — post-purchase/service updates
1. Same inbox flow as A3, but the sent message is a **service update** (e.g., "Your order has shipped 📦 — track it here: ...").
2. Show delivery in Messenger.
3. Say: "For transactional, post-purchase updates we send utility messages through the same authorized channel."

### A5. `pages_read_engagement` — reading Page engagement metrics
1. Open `hudhd.com/analytics` → Page Performance section → show reach/impressions/engagement charts with real numbers.
2. Hover a metric; say: "These engagement metrics are read live from the client's Page via the Graph API."
3. Show a date-range change → numbers update.

### A6. `pages_read_user_content` — reading Page posts/content
1. Show our app's synced Page content (Studio → published/synced posts list showing real post texts from the Page feed).
2. Open the Facebook Page in tab 2 → show the same posts exist publicly.
3. Say: "Hudhud reads the Page's existing posts and content to build the AI's knowledge base."

### A7. `pages_manage_posts` — creating/publishing Page posts
1. Open `hudhd.com/studio` → create a short post (AI generate or type) → **Publish to Facebook Page**.
2. Show the success state → open the Facebook Page tab → **show the new post live on the Page**.
3. Say: "pages_manage_posts lets Hudhud publish and manage posts on the client's Page on their behalf."

### A8. `pages_manage_engagement` — engaging with Page content (hide/like comment)
1. Open inbox/comments moderation view (or Studio comments section).
2. Show a comment on a Page post → perform the moderation action available (hide spam comment / like).
3. Show the result reflected (comment hidden on the Page in tab 2 if possible).
4. Say: "Our agents can moderate engagement on the client's Page — hiding spam, liking customer comments — through pages_manage_engagement."

### A9. `pages_manage_ads` — Page ads posts access
1. Show our app's marketing/analytics section reading the Page's ad posts (`ads_posts`) — the ads data integrated in Hudhud.
2. Tab 2: Meta Ads Manager showing the Page's campaign.
3. Say: "For clients running ads, Hudhud reads and manages their Page's ad posts and performance through pages_manage_ads."

---

## 📸 GROUP B — Instagram (@karim__abdalwahid — via Facebook login)

### B1. `instagram_basic` — the connected IG professional account
1. `hudhd.com/settings` → show the Instagram account connected: **@karim__abdalwahid** (username, followers, media count from the API).
2. Tab 2: Meta dashboard → Instagram accounts → the same account linked to the Page.
3. Say: "instagram_basic lets Hudhud read the client's Instagram professional account identity — username, followers, media."

### B2. `instagram_manage_messages` — IG DMs (CORE — 90s)
1. `hudhd.com/inbox` → filter/point at a real **Instagram DM conversation** (platform indicator = Instagram).
2. Show the AI reply in the thread → Human takeover reply → **Send**.
3. Show delivery in the Instagram app (phone) or instagram.com DMs.
4. Say: "Instagram DMs flow into the same unified inbox — the AI replies within the 24-hour window, humans can take over — via instagram_manage_messages."

### B3. `instagram_manage_comments` — reading & replying to IG comments
1. Show the comments section (inbox/comments view) with real IG comments on a Reel/post.
2. Show our reply to a comment (auto or manual).
3. Show the comment reply live on Instagram.
4. Say: "Comment inquiries on Reels and posts are captured and answered — turning comments into sales conversations."

### B4. `instagram_manage_insights` — IG account insights
1. `hudhd.com/analytics` → Instagram section → reach, follower growth, impressions with real data.
2. Say: "instagram_manage_insights powers the performance dashboards our clients use to track growth."

### B5. `instagram_content_publish` — publishing to IG
1. `hudhd.com/studio` → create an IG post/reel → **Publish/Schedule to Instagram**.
2. Show the success + open instagram.com → **show the published post live**.
3. Say: "Hudhud publishes Reels and posts to the client's Instagram through instagram_content_publish."

### B6. `instagram_manage_contents` — managing existing IG content
1. Show the media management view: list of the client's IG media (posts/reels) with status.
2. Open instagram.com → the same posts.
3. Say: "Clients manage their existing Instagram content — reviewing and organizing their media — through instagram_manage_contents."

### B7. `instagram_manage_engagement` — engaging with IG content
1. Comments moderation view → hide a spam comment on an IG post (or like a comment).
2. Show the result on instagram.com (comment hidden/liked).
3. Say: "instagram_manage_engagement lets our agents protect the client's Instagram community — hiding spam and engaging with customers."

---

## 🧵 GROUP C — Threads (@karim__abdalwahid)

### C1. `threads_basic` — the connected Threads profile
1. `hudhd.com/settings` → Threads section → show connected profile **@karim__abdalwahid** (from the official Threads OAuth).
2. Say: "Through the official Threads OAuth, Hudhud reads the client's Threads profile identity via threads_basic."

### C2. `threads_content_publish` — publishing a Threads post
1. Studio → compose a short Threads post → **Publish to Threads**.
2. Show success → open threads.net → **show the post live**.
3. Say: "threads_content_publish lets our AI publish content to the client's Threads account."

### C3. `threads_read_replies` — reading replies to Threads posts
1. Show the replies view for a published Threads post (replies listed with usernames).
2. Open threads.net → show the same replies exist.
3. Say: "Every reply to the client's Threads posts is read through threads_read_replies and can trigger agent engagement."

### C4. `threads_manage_replies` — managing replies
1. Show reply management (viewing reply threads for moderation).
2. Say: "threads_manage_replies allows Hudhud to organize and manage reply conversations on the client's behalf."

### C5. `threads_manage_insights` — Threads insights
1. Show the insights view: views/likes/replies metrics for the Threads account/posts.
2. Say: "threads_manage_insights powers the Threads performance metrics in our analytics."

### C6. `threads_delete` — deleting a Threads post
1. Studio/Threads management → select a published test post → **Delete** → confirm.
2. Open threads.net → **show the post is gone**.
3. Say: "Clients can remove published content directly from Hudhud — via threads_delete."

---

## 🧩 GROUP D — Business & Account permissions

### D1. `business_management` — the business portfolio behind the platform
1. Tab 1: Meta Business Settings → show the business portfolio with the Hudhud app + assets (the Page, IG account) assigned.
2. Tab 2: `hudhd.com/admin` (our admin console) — show the platform operating those assets.
3. Say: "business_management connects the client's business assets — Pages, Instagram accounts — to the Hudhud platform they subscribed to."

### D2. `read_insights` — Page insights metrics
1. `hudhd.com/analytics` → show page_post_engagements, impressions, reach time series (real numbers).
2. Say: "read_insights powers every performance report in Hudhud — reach, engagement, trends, root causes."

### D3. `ads_read` — reading ad performance
1. Show our app's campaigns/ads performance view (synced campaign metrics).
2. Tab 2: Meta Ads Manager showing the same campaign.
3. Say: "ads_read lets Hudhud pull ad performance into the client's unified dashboard."

### D4. `ads_management` — managing ads
1. Show the ads section in our app (campaign view/management).
2. Tab 2: Meta Ads Manager with the campaign the app manages.
3. Say: "For clients who run paid campaigns, Hudhud manages their ads through ads_management."

### D5. `leads_retrieval` — Lead Ads → CRM (CORE)
1. Show a Meta Lead Ads form (Ads Manager → forms).
2. `hudhd.com/leads` → **show the imported leads with full provenance** (source = lead form, timestamps, fields).
3. Say: "leads_retrieval imports every lead from the client's Lead Ads straight into our CRM — zero manual entry, full provenance."

### D6. `public_profile` — user identity in the platform
1. Show the login (Google/Facebook) → after login, the topbar shows the user's **name and profile photo**.
2. Open `/users` (admin) → user profile fields visible.
3. Say: "public_profile gives each signed-in user their name and avatar across the platform."

### D7. `email` — account email
1. `/users` admin page → show user emails listed.
2. Show notifications sent to the user's email (or the login screen prefilled).
3. Say: "email is used for account identity, receipts and product notifications — stored encrypted-at-rest standards, never sold."

### D8. `Human Agent` — human replies beyond the 24h window (CORE — 90s)
1. `hudhd.com/inbox` → open a conversation **older than 24 hours** (show the timestamp).
2. Click **Human Takeover** → type a human support reply → **Send** → show delivery in Messenger.
3. Say: "Human Agent lets our clients' human support teams reply to customers beyond the 24-hour window — bots never do this; only real human agents, which is exactly what this permission is for."

### D9. `Business Asset User Profile Access` — customer profiles from messaging
1. `hudhd.com/inbox` → open a conversation → show the customer's profile card (name, platform identity, linked accounts).
2. `/leads` → show the same lead's captured profile with provenance.
3. Say: "When customers message our clients, Business Asset User Profile Access lets Hudhud show who they are — names and profile info — so replies are personal and leads are properly identified."

---

## ✅ FINAL CHECKLIST (before submitting all files)
- [ ] 31 videos, one per permission, named exactly like the permission string.
- [ ] Every video: single take, URL bar visible, English narration, real data.
- [ ] Every "show delivery/live proof" step actually shown (Messenger/IG/Threads second tab or phone).
- [ ] No secrets visible (never show `.env`, API keys, or tokens on screen — blur if a token ever appears).
- [ ] Upload each video to the matching permission in App Review → Permissions and Features → screencast field.

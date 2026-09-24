# 🎥 Meta App Review — Screencast Recording Master Guide & AI Agent Prompts
**App Name**: Hudhud (`هدهد · Hudhud`)  
**App ID**: `2092880431308591`  
**Base Web URL**: `https://www.hudhd.com` (or `http://localhost:8000`)  
**Language for Recordings**: English (`?lang=en` query parameter recommended for international reviewers)  

---

## 📌 Executive Summary & Meta Screencast Standards

Meta App Reviewers strictly evaluate screencasts against the following mandatory rules:
1. **Show End-to-End User Experience**: The video must show the actual user interface, how a user triggers the feature, and what happens as a result.
2. **Clear App Identity**: The browser URL bar (showing `https://www.hudhd.com` or local dev URL) and the App Logo/Name ("Hudhud") must be visible.
3. **English Interface**: All screens, inputs, and buttons should be in English so global review teams can evaluate immediately.
4. **No Placeholders or Broken Actions**: Every click must result in an immediate visual update (e.g., status badge change, sent message bubble, created post card, modal confirmation).
5. **Human Oversight & Consent**: For automated or publishing actions, show that the user has full control (toggles, edit options, delete buttons).

---

## 🛠️ Part 1: Resolving the 2 Missing API Test Calls

Meta App Review requires that your application has performed at least one real API test call in Development Mode for:
1. `threads_manage_replies`
2. `instagram_business_manage_comments`

### Why this happens:
Meta tracks Graph API endpoint hits. If an app has never called `POST /{comment-id}/replies` or the Threads reply endpoints, the submission dashboard displays:
`Ensure you have performed required API test calls` and blocks final submission.

### How to resolve:
1. **For `instagram_business_manage_comments`**:
   - Make a Graph API call using the Page Access Token to post a reply to an Instagram comment:
   ```bash
   POST https://graph.facebook.com/v21.0/{ig-comment-id}/replies
   message="Thank you for your comment! Hudhud automated reply test."
   access_token={PAGE_ACCESS_TOKEN}
   ```
   Or run the provided script `python scripts/perform_api_test_calls.py --channel instagram`.

2. **For `threads_manage_replies`**:
   - Make a call to Threads Graph API:
   ```bash
   POST https://graph.threads.net/v1.0/{threads-media-id}/replies
   text="Test reply from Hudhud AI Agent"
   access_token={THREADS_USER_TOKEN}
   ```
   - Once executed, wait 2–5 minutes and refresh Meta Developer Submissions; the warning status turns green / satisfied.

---

## 🎬 Part 2: Detailed Recording Prompts for the 29 Permissions

Below is the exact prompt and step-by-step navigation script for each permission, designed for an AI Browser Agent (or manual recording session).

---

### 1. `human_agent`
* **Permission Purpose**: Allows human agents to respond to customer inquiries on Messenger/Instagram outside the standard 24-hour messaging window (up to 7 days) using the official `HUMAN_AGENT` message tag.
* **Target URL**: `https://www.hudhd.com/inbox?lang=en`
* **Agent Navigation & Recording Script**:
  1. Navigate to `/inbox?lang=en`.
  2. In the conversation list (left column), click on an existing customer conversation (e.g., "Sarah Miller - Instagram Direct").
  3. Point the cursor to the top action bar of the chat stream where the **"Human Takeover (تولي المحادثة)"** toggle button is located.
  4. Click the **"Human Takeover"** toggle.
  5. Observe the UI banner appear: *"Human Agent Mode Active — AI automation paused for 24 hours. Messages tagged with HUMAN_AGENT."*
  6. In the message input field at the bottom, type:
     `"Hello Sarah, this is a human customer support agent following up on your inquiry from last week. How can I assist you today?"`
  7. Click the **"Send"** button.
  8. Show the message bubble appear in the chat stream with the blue **"Human Agent"** badge and timestamp.
* **Reviewer Verification**: Confirms that human takeover is explicitly initiated by a human user, pauses automated bots, and tags the outbound message properly.

---

### 2. `business_asset_user_profile_access`
* **Permission Purpose**: Allows the app to retrieve public profile information (name, avatar, locale) of users who interact with the business page or account.
* **Target URL**: `https://www.hudhd.com/inbox?lang=en` or `https://www.hudhd.com/leads?lang=en`
* **Agent Navigation & Recording Script**:
  1. Navigate to `/inbox?lang=en`.
  2. Select a customer conversation in the left column.
  3. Focus the recording on the **3rd column (Customer Profile Dossier)** on the right side.
  4. Highlight the customer's avatar picture, full name, social handle, and platform badge (Instagram/Facebook).
  5. Scroll through the Dossier showing:
     - Lead Status (`Warm`, `Qualified`)
     - Inbound channel & first contact timestamp
     - Interaction summary and tags.
  6. Click the link **"View in Leads CRM →"** which opens `/leads?lang=en`.
  7. Show the customer record in the CRM table with full verified profile data.
* **Reviewer Verification**: Shows that profile data is used strictly inside the CRM/Inbox to contextualize customer service and manage leads.

---

### 3. `pages_show_list`
* **Permission Purpose**: Discovers and lists Facebook Pages that the user manages, enabling the user to select which page to connect to Hudhud.
* **Target URL**: `https://www.hudhd.com/settings?lang=en`
* **Agent Navigation & Recording Script**:
  1. Navigate to `/settings?lang=en`.
  2. Scroll to the **"Connected Facebook Pages"** section.
  3. Click **"Refresh Pages List"** or observe the active page cards.
  4. Show the list displaying:
     - Facebook Page Name (e.g., `Hudhd`)
     - Page ID (`1108892288983475`)
     - Connection status badge (`Connected / Active`)
     - Permissions granted badge.
  5. Toggle the page connection switch to show how the user selects or disconnects specific pages.
* **Reviewer Verification**: Proves the app only accesses pages explicitly authorized and selected by the user.

---

### 4. `pages_manage_metadata`
* **Permission Purpose**: Manages Page settings and configures webhook subscriptions for receiving real-time messaging and feed events.
* **Target URL**: `https://www.hudhd.com/settings?lang=en`
* **Agent Navigation & Recording Script**:
  1. Navigate to `/settings?lang=en`.
  2. Scroll down to the **"Webhooks & Meta App Integration"** panel.
  3. Display the Webhook Callback URL (`https://www.hudhd.com/webhooks/meta`) and Verify Token status (`Verified ✅`).
  4. Show the list of subscribed event topics: `messages`, `messaging_postbacks`, `feed`, `mention`.
  5. Click the **"Test Webhook Handshake"** or **"Sync Subscriptions"** button.
  6. Observe the green confirmation toast: *"Webhook subscriptions verified and synced with Page metadata."*
* **Reviewer Verification**: Confirms metadata access is solely used to subscribe the Page to necessary webhooks for live inbox notifications.

---

### 5. `pages_utility_messaging`
* **Permission Purpose**: Allows sending non-promotional utility notifications (e.g., appointment confirmations, order status updates, account alerts) to users on Messenger.
* **Target URL**: `https://www.hudhd.com/automations?lang=en`
* **Agent Navigation & Recording Script**:
  1. Navigate to `/automations?lang=en`.
  2. Locate the pre-configured workflow: **"Booking Confirmation & Appointment Reminder"**.
  3. Click **"Edit Workflow"**.
  4. Show the trigger: *"User books a consultation via calendar link"*.
  5. Show the action block: *"Send Messenger Utility Notification (Tag: CONFIRMED_EVENT_UPDATE)"*.
  6. Display the message template:
     `"Your consultation with Hudhud team is confirmed for tomorrow at 3:00 PM. Click here to reschedule or view details."`
  7. Click the **"Test Notification"** button to simulate sending the utility message to a test user.
* **Reviewer Verification**: Proves the messages are 100% utility/transactional with no promotional content, adhering to Meta's utility messaging policy.

---

### 6. `pages_messaging`
* **Permission Purpose**: Enables two-way communication between customers and the Facebook Page on Messenger.
* **Target URL**: `https://www.hudhd.com/inbox?lang=en`
* **Agent Navigation & Recording Script**:
  1. Navigate to `/inbox?lang=en`.
  2. Filter by **"Facebook Messenger"** channel button.
  3. Click an active Messenger conversation (e.g., "Ahmed Hassan").
  4. Show the incoming customer message: *"Hello, what are your opening hours and location?"*
  5. In the message box, type:
     `"Hi Ahmed! Our office is open Sunday to Thursday from 9 AM to 6 PM. You can also reach us anytime online."`
  6. Click **"Send"** (or press Enter).
  7. Highlight the message appearing immediately in the conversation thread with a "Delivered" checkmark.
* **Reviewer Verification**: Demonstrates a complete live two-way customer support chat on Facebook Messenger.

---

### 7. `business_management`
* **Permission Purpose**: Allows reading and managing assets, ad accounts, and pages within the user's Meta Business Portfolio.
* **Target URL**: `https://www.hudhd.com/settings?lang=en` & `/dashboard?lang=en`
* **Agent Navigation & Recording Script**:
  1. Navigate to `/settings?lang=en`.
  2. Scroll to the **"Meta Business Portfolio & Assets"** card.
  3. Show the Business Account Name, Business ID, linked Ad Accounts, and assigned Pages.
  4. Navigate to `/dashboard?lang=en` (Overview).
  5. Show the multi-asset overview card displaying consolidated metrics across all business assets managed under the portfolio.
* **Reviewer Verification**: Shows how business assets are linked and managed centrally by the business administrator.

---

### 8. `pages_read_engagement`
* **Permission Purpose**: Allows the app to read engagement metrics (likes, reactions, comments count, shares) on Facebook Page posts.
* **Target URL**: `https://www.hudhd.com/studio?lang=en` & `/analytics?lang=en`
* **Agent Navigation & Recording Script**:
  1. Navigate to `/studio?lang=en`.
  2. Scroll down to the **"Live Meta Feed Grid"**.
  3. Click the filter button **"Facebook"**.
  4. Hover over several Facebook post cards to highlight the engagement counters:
     - Likes count (e.g. `❤️ 142`)
     - Comments count (e.g. `💬 28`)
     - Shares count (e.g. `🔁 12`)
  5. Navigate to `/analytics?lang=en` and highlight the **"Page Engagement Trends"** chart showing daily likes and interaction rates over the past 30 days.
* **Reviewer Verification**: Shows engagement data being collected and displayed to help page owners understand post performance.

---

### 9. `threads_content_publish`
* **Permission Purpose**: Publishes text threads and media directly to the user's Meta Threads account.
* **Target URL**: `https://www.hudhd.com/studio?lang=en`
* **Agent Navigation & Recording Script**:
  1. Navigate to `/studio?lang=en`.
  2. Click the **"+ Create Post"** button to open the Content Composer modal.
  3. Under the **"Select Platform"** selector, click **"Threads"** (with Threads logo).
  4. In the post text area, type:
     `"Excited to share our latest product update with the community! Autonomous AI social selling is here. #Hudhud #BuildInPublic"`
  5. Observe the character counter (under 500 chars limit for Threads).
  6. Click **"Publish Now"**.
  7. Show the loading state changing to a success alert: *"Successfully published to Threads! Thread ID: 179...".*
  8. Scroll down to the Feed Grid to see the newly published thread card.
* **Reviewer Verification**: Demonstrates a clear composer flow resulting in a successful Threads post publication.

---

### 10. `threads_delete`
* **Permission Purpose**: Deletes published threads from the user's Threads account.
* **Target URL**: `https://www.hudhd.com/studio?lang=en`
* **Agent Navigation & Recording Script**:
  1. Navigate to `/studio?lang=en`.
  2. In the Live Meta Feed Grid, filter by **"Threads"**.
  3. Locate a published thread card.
  4. Click the three-dots menu or **"Delete"** trash icon on the card.
  5. A confirmation dialog appears: *"Are you sure you want to permanently delete this thread from Threads?"*.
  6. Click **"Confirm Delete"**.
  7. Show the card smoothly disappearing with a toast notification: *"Thread successfully deleted from Meta Threads."*
* **Reviewer Verification**: Proves deletion is strictly initiated by the user with an explicit confirmation step.

---

### 11. `threads_manage_insights`
* **Permission Purpose**: Accesses analytics and performance metrics (views, likes, reposts, quotes) for Threads posts and profile.
* **Target URL**: `https://www.hudhd.com/analytics?lang=en`
* **Agent Navigation & Recording Script**:
  1. Navigate to `/analytics?lang=en`.
  2. Click the **"Threads Analytics"** tab.
  3. Highlight the KPI metric cards:
     - **Thread Views / Impressions**: `45,210` (+14.2%)
     - **Total Likes**: `1,840`
     - **Reposts & Quotes**: `312`
     - **Replies Ingested**: `189`
  4. Scroll to the **"Top Threads by Engagement"** table and expand a row to show detailed hourly performance graphs.
* **Reviewer Verification**: Confirms that Threads insights are aggregated into clear executive dashboards for the business owner.

---

### 12. `threads_manage_replies`
* **Permission Purpose**: Allows managing replies to Threads posts, including replying back, hiding replies, or moderating conversations.
* **Target URL**: `https://www.hudhd.com/inbox?lang=en` or `/automations?lang=en`
* **Agent Navigation & Recording Script**:
  1. Navigate to `/inbox?lang=en`.
  2. Switch the channel filter to **"Threads Replies"**.
  3. Click on a thread conversation where a user asked: *"Does this integrate with Shopify?"*.
  4. In the reply box, type:
     `"Yes! Hudhud seamlessly connects with Shopify to track orders and answer customer stock questions."`
  5. Click **"Reply on Threads"**.
  6. Show the response appended to the thread replies tree with a confirmation checkmark.
  7. (Optional) Show the "Hide Reply" option for moderating inappropriate comments.
* **Reviewer Verification**: Shows direct community management and replies to Threads discussions.

---

### 13. `threads_manage_mentions`
* **Permission Purpose**: Monitors and responds to public mentions of the Threads account across the platform.
* **Target URL**: `https://www.hudhd.com/inbox?lang=en`
* **Agent Navigation & Recording Script**:
  1. Navigate to `/inbox?lang=en`.
  2. Click the **"Mentions"** tab.
  3. Highlight an incoming item: *"@hudhud can you help me check if your AI agent supports Arabic?"*.
  4. Click the mention card to open the action panel.
  5. Click **"Respond to Mention"**, enter:
     `"Hello! Yes, Hudhud has full native support for Arabic and English."`
  6. Click **"Publish Reply"**. Show the mention marked as resolved/responded.
* **Reviewer Verification**: Shows how incoming brand mentions on Threads are detected and managed.

---

### 14. `threads_read_replies`
* **Permission Purpose**: Reads incoming replies and conversation trees on the user's Threads posts.
* **Target URL**: `https://www.hudhd.com/studio?lang=en` or `/inbox?lang=en`
* **Agent Navigation & Recording Script**:
  1. Navigate to `/studio?lang=en`.
  2. Click on a published Threads card to open the **"Thread Details & Community Discussion"** modal.
  3. Highlight the conversation list showing multiple user replies with their usernames, avatars, and reply timestamps.
  4. Scroll down to show threaded nested replies loaded from the Threads API.
* **Reviewer Verification**: Confirms that reading replies is used to show community feedback to the creator.

---

### 15. `instagram_business_content_publish`
* **Permission Purpose**: Publishes single images, carousels, or Reels directly to the connected Instagram Business account.
* **Target URL**: `https://www.hudhd.com/studio?lang=en`
* **Agent Navigation & Recording Script**:
  1. Navigate to `/studio?lang=en`.
  2. Click **"+ Create Post"**.
  3. Select **"Instagram"** as the target platform.
  4. Select Post Type: **"Reel / Video"** (or "Image Post").
  5. Enter a media URL or select an asset from the media library.
  6. In the caption box, write:
     `"Boost your social selling conversion with Hudhud AI. Link in bio to start your free trial! 🚀 #marketing #ai"`
  7. Click **"Publish to Instagram"**.
  8. Show the status change: *"Container created → Video processed → Published successfully! Media ID: 178..."*.
* **Reviewer Verification**: Demonstrates complete Instagram container creation and media publishing flow.

---

### 16. `instagram_business_manage_insights`
* **Permission Purpose**: Reads account-level performance insights (reach, impressions, profile visits, follower demographics) for Instagram Business accounts.
* **Target URL**: `https://www.hudhd.com/analytics?lang=en`
* **Agent Navigation & Recording Script**:
  1. Navigate to `/analytics?lang=en`.
  2. Click the **"Instagram Business"** analytics tab.
  3. Point the cursor to the KPI cards:
     - **Accounts Reached**: `128,450` (+22.4%)
     - **Profile Visits**: `3,820`
     - **Website Taps**: `940`
  4. Scroll to the **"Audience Demographics"** breakdown (City, Age, Gender distribution charts).
* **Reviewer Verification**: Shows compliant aggregation and visual reporting of Instagram business metrics.

---

### 17. `instagram_business_manage_comments`
* **Permission Purpose**: Reads comments on Instagram posts and Reels, and enables public replies and private DM responses.
* **Target URL**: `https://www.hudhd.com/automations?lang=en`
* **Agent Navigation & Recording Script**:
  1. Navigate to `/automations?lang=en`.
  2. Click on the active rule: **"Instagram Reel Comment-to-DM Engine"**.
  3. Show the trigger: *"User comments with keyword 'PRICE' on any Reel"*.
  4. Show Action 1: *"Reply publicly to comment with: 'Sent you all the details in your DM! 📩 Check your inbox!'"*.
  5. Show Action 2: *"Send private DM to commenter with catalog link and discount code"*.
  6. Click the **"Test Automation Live"** button.
  7. Show the simulated comment receiving both the public reply and the private DM.
* **Reviewer Verification**: Clear demonstration of the auto-reply to comments workflow complying with Instagram messaging rules.

---

### 18. `instagram_manage_engagement`
* **Permission Purpose**: Manages engagement interactions (liking comments, managing comment interactions) on Instagram content.
* **Target URL**: `https://www.hudhd.com/automations?lang=en`
* **Agent Navigation & Recording Script**:
  1. Navigate to `/automations?lang=en`.
  2. Open the workflow builder.
  3. Highlight the action step: **"Auto-Like Comment"** toggled to ON.
  4. Show the explanation text: *"Automatically likes positive customer comments to increase algorithmic reach and show appreciation."*
  5. Trigger the test run to show the comment receiving a like reaction (`❤️ Liked by Page`).
* **Reviewer Verification**: Demonstrates how engagement like reactions are automated safely and contextually.

---

### 19. `instagram_manage_contents`
* **Permission Purpose**: Manages and inspects the Instagram media library, including viewing published Reels, photos, and captions.
* **Target URL**: `https://www.hudhd.com/studio?lang=en`
* **Agent Navigation & Recording Script**:
  1. Navigate to `/studio?lang=en`.
  2. In the **Live Meta Feed Grid**, click the **"Instagram"** filter tab.
  3. Scroll through the grid showing real Instagram Reels and posts with their cover thumbnails, caption snippets, and publish dates.
  4. Click the **"View on Instagram ↗"** link on a post to prove it directly links to the live Instagram permalink.
* **Reviewer Verification**: Shows that the app fetches, organizes, and displays the user's Instagram content library.

---

### 20. `instagram_manage_insights`
* **Permission Purpose**: Accesses post-level insights for individual Instagram media items (plays, saves, likes, retention).
* **Target URL**: `https://www.hudhd.com/studio?lang=en` & `/analytics?lang=en`
* **Agent Navigation & Recording Script**:
  1. Navigate to `/studio?lang=en`.
  2. Click on any Instagram Reel card to open the **"Reel Analytics"** modal.
  3. Highlight the specific metrics:
     - **Reel Plays**: `14,230`
     - **Saves**: `245`
     - **Shares**: `89`
     - **Average Watch Time**: `12.4s`
* **Reviewer Verification**: Proves detailed media-level analytics are displayed for content optimization.

---

### 21. `instagram_business_basic`
* **Permission Purpose**: Accesses basic profile data of the Instagram Business account (username, bio, profile photo, follower count).
* **Target URL**: `https://www.hudhd.com/settings?lang=en`
* **Agent Navigation & Recording Script**:
  1. Navigate to `/settings?lang=en`.
  2. Scroll to the **"Connected Instagram Business Account"** section.
  3. Highlight:
     - Profile picture avatar
     - Username (e.g. `@hudhud_official`)
     - Account ID (`17841459820747642`)
     - Account Type: `Professional / Business Account`
     - Followers count.
* **Reviewer Verification**: Demonstrates basic profile details used strictly for account identification.

---

### 22. `instagram_business_manage_messages`
* **Permission Purpose**: Manages incoming and outgoing Direct Messages (DMs) for Instagram Business accounts.
* **Target URL**: `https://www.hudhd.com/inbox?lang=en`
* **Agent Navigation & Recording Script**:
  1. Navigate to `/inbox?lang=en`.
  2. Select the **"Instagram Direct"** filter.
  3. Click a conversation thread with an Instagram user.
  4. Show customer query: *"Can I get a discount code for my first order?"*.
  5. In the reply box, type:
     `"Here is a 15% discount code for your first purchase: WELCOME15! Let me know if you need help checkout."`
  6. Click **"Send"**. Show the outgoing message displayed instantly with delivery state.
* **Reviewer Verification**: Demonstrates full DM management for Instagram Business.

---

### 23. `pages_read_user_content`
* **Permission Purpose**: Reads user-generated content on the Facebook Page, such as visitor posts and community comments.
* **Target URL**: `https://www.hudhd.com/studio?lang=en` & `/inbox?lang=en`
* **Agent Navigation & Recording Script**:
  1. Navigate to `/studio?lang=en`.
  2. Click on a Facebook post card.
  3. Open the **"User Comments & Feedback"** drawer.
  4. Show comments written by community members on the Page post.
  5. Navigate to `/inbox?lang=en` to show incoming community questions captured from page interactions.
* **Reviewer Verification**: Shows compliant reading of community user content for customer service.

---

### 24. `pages_manage_posts`
* **Permission Purpose**: Creates, schedules, edits, and publishes posts on the Facebook Page.
* **Target URL**: `https://www.hudhd.com/studio?lang=en`
* **Agent Navigation & Recording Script**:
  1. Navigate to `/studio?lang=en`.
  2. Click **"+ Create Post"**.
  3. Select **"Facebook Page"**.
  4. Type the post content:
     `"We are thrilled to announce new features in our platform today! Check out our website to learn more."`
  5. Choose **"Schedule for Later"** or **"Publish Now"**.
  6. Click the blue **"Publish Post"** button.
  7. Show the newly created post appearing at the top of the feed grid with the green **"Published"** badge.
* **Reviewer Verification**: Demonstrates full post creation, scheduling, and publication management on Facebook.

---

### 25. `pages_manage_engagement`
* **Permission Purpose**: Moderates and manages engagement on Facebook Page posts (liking, replying to, and hiding comments).
* **Target URL**: `https://www.hudhd.com/automations?lang=en` & `/studio?lang=en`
* **Agent Navigation & Recording Script**:
  1. Navigate to `/automations?lang=en`.
  2. Show the **"Facebook Page Comment Auto-Reply"** automation rule.
  3. Show how incoming comments containing specific questions are automatically replied to.
  4. Navigate to `/studio?lang=en`, open post comments, and click the **"Like"** reaction button next to a user's comment to like it as the Page.
* **Reviewer Verification**: Shows page engagement moderation and interactions.

---

### 26. `instagram_manage_comments`
* **Permission Purpose**: Moderates and handles comments on Instagram posts, including sentiment filtering and auto-replies.
* **Target URL**: `https://www.hudhd.com/automations?lang=en`
* **Agent Navigation & Recording Script**:
  1. Navigate to `/automations?lang=en`.
  2. Click **"+ New Automation Rule"**.
  3. Select Platform: **"Instagram Comments"**.
  4. Set keyword filter: `help, support, info`.
  5. Configure automated reply template:
     `"We are here to help! Please send us a direct message and our team will assist immediately."`
  6. Save and activate the automation.
* **Reviewer Verification**: Shows comprehensive comment management and automation rule builder.

---

### 27. `threads_basic`
* **Permission Purpose**: Reads basic profile data for the authenticated Threads user (username, avatar, bio).
* **Target URL**: `https://www.hudhd.com/settings?lang=en`
* **Agent Navigation & Recording Script**:
  1. Navigate to `/settings?lang=en`.
  2. Scroll to the **"Meta Threads Connection"** card.
  3. Highlight:
     - Threads Handle: `@hudhud_app`
     - Threads Profile picture
     - Threads Bio: *"AI Social Selling & Messaging Automation"*
     - Connection status: `Authorized ✅`
* **Reviewer Verification**: Verifies that Threads basic profile is used solely for identifying the account.

---

### 28. `instagram_manage_messages`
* **Permission Purpose**: Sends and receives messages on Instagram Direct for conversational customer service.
* **Target URL**: `https://www.hudhd.com/inbox?lang=en`
* **Agent Navigation & Recording Script**:
  1. Navigate to `/inbox?lang=en`.
  2. Select an ongoing Instagram chat.
  3. Show the live chat stream.
  4. Type a helpful reply:
     `"Sure! You can track your order status directly using your tracking number here: https://hudhd.com/track"`
  5. Click **"Send"**.
  6. Highlight the message timestamp and delivery confirmation.
* **Reviewer Verification**: Shows live interactive messaging on Instagram Direct.

---

### 29. `read_insights`
* **Permission Purpose**: Accesses aggregated Graph API insights and metrics across connected pages and business assets.
* **Target URL**: `https://www.hudhd.com/analytics?lang=en`
* **Agent Navigation & Recording Script**:
  1. Navigate to `/analytics?lang=en`.
  2. Highlight the top Executive KPI summary:
     - **Consolidated Reach**: `245,800` (+18.5%)
     - **Overall Engagement Rate**: `4.8%`
     - **Net New Inbound Leads**: `612`
     - **Conversion Rate**: `12.4%`
  3. Switch time range selector (`Last 7 Days` → `Last 30 Days`).
  4. Show charts refreshing with live data points.
* **Reviewer Verification**: Confirms overall read_insights permission is used to provide consolidated business analytics.

---

### 30. `instagram_basic`
* **Permission Purpose**: Reads basic account profile info (user ID, username, account type, media count) for the authenticated Instagram account.
* **Target URL**: `https://www.hudhd.com/settings?lang=en`
* **Agent Navigation & Recording Script**:
  1. Navigate to `/settings?lang=en`.
  2. Locate the **"Instagram Basic Display & Account Profile"** card.
  3. Highlight:
     - Instagram Username: `@hudhud_official`
     - Instagram User ID: `17841459820747642`
     - Account Type: `BUSINESS_ACCOUNT`
     - Media Count: `58 Posts`
  4. Click **"Sync Basic Account Info"**.
  5. Display confirmation toast: `GET /v21.0/17841459820747642?fields=id,username,account_type,media_count · HTTP 200 OK`.
* **Reviewer Verification**: Verifies that instagram_basic is used strictly to identify the connected Instagram business account and synchronize account metadata.

---

## 🚀 Part 3: Sequential Recording Execution Protocol

When recording screencasts using `browser_subagent`:
1. **Start with Permission #1 (`human_agent`)**.
2. Perform the exact script steps smoothly (deliberate mouse movements, clear clicks, 1-second pause after key actions).
3. The video recording will be automatically saved to the conversation artifacts directory.
4. **Halt execution and present the video link and summary to the user for approval.**
5. Upon user approval, proceed to Permission #2.
6. Repeat until all 29 screencasts are recorded and verified.

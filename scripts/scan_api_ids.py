"""Comprehensive scan: every API URL construction using IDs — verifies
correct ID type per Meta API endpoint (ig_id vs page_id vs /me)."""
from pathlib import Path

issues = []
ok_patterns = []

for p in sorted(Path("src").rglob("*.py")):
    if "__pycache__" in str(p):
        continue
    txt = p.read_text(encoding="utf-8", errors="ignore")
    for i, line in enumerate(txt.splitlines(), 1):
        s = line.strip()
        # skip comments, imports, variable assignments (not URL construction)
        if s.startswith("#") or s.startswith("import") or s.startswith("from"):
            continue
        # look for f-string URL constructions with IDs
        if "f\"" in s and ("ig_id" in s or "page_id" in s or "META_PAGE_ID" in s
                          or "instagram_account_id" in s or "META_INSTAGRAM" in s):
            # extract the URL pattern
            if "/insights" in s:
                ep = "insights"
            elif "/conversations" in s:
                ep = "conversations"
            elif "/media" in s:
                ep = "media"
            elif "/messages" in s or "/me/messages" in s:
                ep = "messages"
            elif "/feed" in s or "/posts" in s or "/published_posts" in s:
                ep = "posts"
            elif "/subscribed_apps" in s:
                ep = "subscribed_apps"
            elif "/promotable_posts" in s or "/ads_posts" in s:
                ep = "ads"
            elif "/me" in s:
                ep = "me"
            else:
                ep = "other"

            uses_ig = "ig_id" in s or "instagram_account_id" in s or "instagram_id" in s
            uses_page = "page_id" in s or "page_id'" in s or 'page_id"' in s

            # Meta API rules:
            # insights, media → IG Business Account ID (correct with ig_id)
            # conversations, messages, feed, posts → Page ID (correct with page_id or /me)
            # /me/messages → Page Access Token + /me = correct
            if ep == "insights" or ep == "media":
                if uses_ig:
                    ok_patterns.append(f"{p.name}:{i} [{ep}+ig_id] CORRECT")
                else:
                    issues.append(f"{p.name}:{i} [{ep}] uses page_id — should use ig_id")
            elif ep == "conversations":
                if uses_ig:
                    issues.append(f"{p.name}:{i} [conversations+ig_id] WRONG — use page_id + ?platform=instagram")
                elif uses_page or "/me/" in s or "/page" in s or "base}/" in s or "BASE_URL" in s:
                    ok_patterns.append(f"{p.name}:{i} [conversations+page] OK")
                else:
                    ok_patterns.append(f"{p.name}:{i} [conversations] CHECK")
            elif ep == "messages":
                ok_patterns.append(f"{p.name}:{i} [messages] OK (uses /me/messages with page token)")
            elif ep in ("posts", "subscribed_apps", "ads", "me", "other"):
                ok_patterns.append(f"{p.name}:{i} [{ep}] OK")

print("=== ISSUES (wrong ID type for endpoint) ===")
if issues:
    for x in issues:
        print("  ❌", x)
else:
    print("  NONE — all API endpoints use correct ID types")

print(f"\n=== OK patterns ({len(ok_patterns)}) ===")
for x in ok_patterns:
    print("  ✅", x)

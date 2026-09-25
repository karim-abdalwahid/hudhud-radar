import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = "src/agent/orchestrator.py"
src = open(p, encoding="utf-8").read()

# import + resolve once per event (after profile enrichment, before sends)
src = src.replace(
    "from src.meta_api.client import meta_client",
    "from src.meta_api.client import meta_client, resolve_page_token", 1)

old = """        # 7. Send Outbound Response adhering to 24-hr window & Rate Limits.
        # Use the real event timestamp when available (accurate 24h-window basis)."""
new = """        # 7. Send Outbound Response adhering to 24-hr window & Rate Limits.
        # Wave 9.8: prefer the owner's per-page token for this page/account;
        # legacy global token is the fallback (zero behavior change today).
        page_token = resolve_page_token(event.get("recipient_id"))
        # Use the real event timestamp when available (accurate 24h-window basis)."""
assert old in src
src = src.replace(old, new, 1)

src = src.replace(
    """                send_result = await self.client.send_facebook_message(
                    recipient_id=sender_id,
                    message_text=reply_text,
                    last_interaction_time=last_interaction
                )""",
    """                send_result = await self.client.send_facebook_message(
                    recipient_id=sender_id,
                    message_text=reply_text,
                    last_interaction_time=last_interaction,
                    access_token=page_token
                )""", 1)

src = src.replace(
    """                send_result = await self.client.send_instagram_message(
                    recipient_id=sender_id,
                    message_text=reply_text,
                    last_interaction_time=last_interaction
                )""",
    """                send_result = await self.client.send_instagram_message(
                    recipient_id=sender_id,
                    message_text=reply_text,
                    last_interaction_time=last_interaction,
                    access_token=page_token
                )""", 1)

open(p, "w", encoding="utf-8").write(src)
import ast; ast.parse(src)
print("orchestrator wired to per-page tokens")

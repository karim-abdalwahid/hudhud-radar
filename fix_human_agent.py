"""Human-Agent messaging fix: manual human sends use messaging_type=HUMAN_AGENT
(Meta's sanctioned path to message outside the 24h window — the very feature
being submitted for review), plus honest error surfacing."""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 1. client: messaging_type support (both platforms)
p = "src/meta_api/client.py"
src = open(p, encoding="utf-8").read()

src = src.replace(
    """        last_interaction_time: Optional[datetime] = None,
        tag: Optional[str] = None,
        access_token: Optional[str] = None
    ) -> Dict[str, Any]:
        \"\"\"
        Sends a Direct Message to a Facebook Page conversation.
        Strictly enforces the 24-hour messaging window unless a legitimate tag is supplied.
        access_token: per-page token when provided (Wave 9.8), else legacy global.
        \"\"\"
        self._validate_messaging_window(recipient_id, "facebook", last_interaction_time, tag)""",
    """        last_interaction_time: Optional[datetime] = None,
        tag: Optional[str] = None,
        access_token: Optional[str] = None,
        messaging_type: Optional[str] = None
    ) -> Dict[str, Any]:
        \"\"\"
        Sends a Direct Message to a Facebook Page conversation.
        Strictly enforces the 24-hour messaging window unless a legitimate tag or
        an approved human-agent context is supplied.
        access_token: per-page token when provided (Wave 9.8), else legacy global.
        messaging_type: e.g. HUMAN_AGENT — the sanctioned out-of-window path.
        \"\"\"
        if messaging_type != "HUMAN_AGENT":
            self._validate_messaging_window(recipient_id, "facebook", last_interaction_time, tag)""", 1)

src = src.replace(
    """        payload = {
            "recipient": {"id": recipient_id},
            "message": {"text": message_text}
        }
        if tag:
            payload["messaging_type"] = "MESSAGE_TAG"
            payload["tag"] = tag

        try:
            # ZERO-FABRICATION: without a real token we FAIL honestly —
            # no simulated delivery receipts, no fake activity_logs success.
            if not token or token.startswith("your-"):
                logger.error(f"FB DM to {recipient_id} NOT sent""",
    """        payload = {
            "recipient": {"id": recipient_id},
            "message": {"text": message_text}
        }
        if tag:
            payload["messaging_type"] = "MESSAGE_TAG"
            payload["tag"] = tag
        if messaging_type and messaging_type != "MESSAGE_TAG":
            payload["messaging_type"] = messaging_type

        try:
            # ZERO-FABRICATION: without a real token we FAIL honestly —
            # no simulated delivery receipts, no fake activity_logs success.
            if not token or token.startswith("your-"):
                logger.error(f"FB DM to {recipient_id} NOT sent""", 1)
open(p, "w", encoding="utf-8").write(src)
import ast
ast.parse(src)
print("client FB messaging_type support")

# 2. IG same support
src = open(p, encoding="utf-8").read()
i = src.find("async def send_instagram_message")
seg = src[i:i+1400]
seg2 = seg.replace("        last_interaction_time: Optional[datetime] = None\n    ) -> Dict[str, Any]:",
                   "        last_interaction_time: Optional[datetime] = None,\n        access_token: Optional[str] = None,\n        messaging_type: Optional[str] = None\n    ) -> Dict[str, Any]:", 1)
seg2 = seg2.replace("        self._validate_messaging_window(recipient_id, \"instagram\", last_interaction_time)",
                    "        if messaging_type != \"HUMAN_AGENT\":\n            self._validate_messaging_window(recipient_id, \"instagram\", last_interaction_time)", 1)
seg2 = seg2.replace("        token = access_token or self.access_token\n        rate_limiter.check_and_acquire(\"instagram\")", "        token = access_token or self.access_token\n        rate_limiter.check_and_acquire(\"instagram\")", 1)
src = src[:i] + seg2 + src[i+len(seg):]
# IG payload messaging type injection
j = src.find("async def send_instagram_message")
k = src.find("if tag:", j)
assert k > 0
src = src[:k] + ("        if messaging_type and messaging_type != \"MESSAGE_TAG\":\n            payload[\"messaging_type\"] = messaging_type\n"
                + src[k:])
open(p, "w", encoding="utf-8").write(src)
ast.parse(src)
print("client IG messaging_type support")

# 3. inbox helper: pass human-agent mode + honest route errors
p2 = "src/modules/inbox_onboarding/__init__.py"
s2 = open(p2, encoding="utf-8").read()
s2 = s2.replace(
    "async def _send_and_store_agent_message(lead: Dict[str, Any], text: str, extra_meta: Optional[Dict[str, Any]] = None):",
    "async def _send_and_store_agent_message(lead: Dict[str, Any], text: str, extra_meta: Optional[Dict[str, Any]] = None,\n                                       messaging_type: Optional[str] = None):", 1)
s2 = s2.replace(
    "        send_result = await meta_client.send_facebook_message(recipient_id=recipient, message_text=text)",
    "        send_result = await meta_client.send_facebook_message(recipient_id=recipient, message_text=text,\n                                                             messaging_type=messaging_type)", 1)
s2 = s2.replace(
    "        send_result = await meta_client.send_instagram_message(recipient_id=recipient, message_text=text)",
    "        send_result = await meta_client.send_instagram_message(recipient_id=recipient, message_text=text,\n                                                             messaging_type=messaging_type)", 1)
# manual send route: HUMAN_AGENT + graceful 502
s2 = s2.replace(
    "    result = await _send_and_store_agent_message(lead, text, extra_meta={\"sent_by\": \"human\"})",
    """    from src.core.exceptions import MetaAPIError
    try:
        # Human Agent feature: messaging_type HUMAN_AGENT is Meta's sanctioned
        # out-of-window path for human agents (once per user per 7 days).
        result = await _send_and_store_agent_message(lead, text, extra_meta={"sent_by": "human"},
                                                     messaging_type="HUMAN_AGENT")
    except MetaAPIError as e:
        raise HTTPException(status_code=502, detail=f"Meta rejected the message: {str(e)[:240]}")""", 1)
open(p2, "w", encoding="utf-8").write(s2)
ast.parse(s2)
print("inbox manual send now uses HUMAN_AGENT + honest errors")

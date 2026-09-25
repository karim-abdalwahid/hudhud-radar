import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = "src/meta_api/client.py"
src = open(p, encoding="utf-8").read()

# 1. Module-level resolver (pure, testable)
anchor = "class MetaGraphClient:"
resolver = '''def resolve_page_token(account_id: Optional[str]) -> Optional[str]:
    """Wave 9.8: per-user token for a page/account id from platform_connections
    (encrypted at rest). None → callers use the legacy global token. A
    decryption failure is NOT fatal — it degrades to the legacy token."""
    if not account_id or str(account_id).startswith("your-"):
        return None
    try:
        from src.core.supabase_client import supabase_db
        if not supabase_db.is_connected:
            return None
        rows = (supabase_db.select("platform_connections", {"status": "active"}) or [])
        for r in rows:
            if r.get("platform") not in ("facebook", "instagram"):
                continue
            if str(r.get("account_id") or "") != str(account_id):
                continue
            try:
                from src.core.crypto import decrypt_token
                tok = decrypt_token(r.get("access_token_encrypted") or "")
                if tok:
                    return tok
            except Exception as e:
                logger.warning(f"Per-page token decrypt failed for account {account_id} (legacy fallback): {e}")
                return None
    except Exception as e:
        logger.warning(f"Per-page token resolution unavailable: {e}")
    return None


'''
assert anchor in src
src = src.replace(anchor, resolver + anchor, 1)

# 2. send_facebook_message: optional per-token override
old_fb_sig = '''    async def send_facebook_message(
        self,
        recipient_id: str,
        message_text: str,
        last_interaction_time: Optional[datetime] = None,
        tag: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sends a Direct Message to a Facebook Page conversation.
        Strictly enforces the 24-hour messaging window unless a legitimate tag is supplied.
        """
        self._validate_messaging_window(recipient_id, "facebook", last_interaction_time, tag)

        rate_limiter.check_and_acquire("facebook")
        url = f"{self.BASE_URL}/me/messages"
        params = {"access_token": self.access_token}'''
new_fb_sig = '''    async def send_facebook_message(
        self,
        recipient_id: str,
        message_text: str,
        last_interaction_time: Optional[datetime] = None,
        tag: Optional[str] = None,
        access_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sends a Direct Message to a Facebook Page conversation.
        Strictly enforces the 24-hour messaging window unless a legitimate tag is supplied.
        access_token: per-page token when provided (Wave 9.8), else legacy global.
        """
        self._validate_messaging_window(recipient_id, "facebook", last_interaction_time, tag)

        token = access_token or self.access_token
        rate_limiter.check_and_acquire("facebook")
        url = f"{self.BASE_URL}/me/messages"
        params = {"access_token": token}'''
assert old_fb_sig in src
src = src.replace(old_fb_sig, new_fb_sig, 1)

# fail-closed check uses token var
src = src.replace(
    '''            if not self.access_token or self.access_token.startswith("your-"):''',
    '''            if not token or token.startswith("your-"):''', 1)

# 3. send_instagram_message: same override
old_ig = '''        self._validate_messaging_window(recipient_id, "instagram", last_interaction_time)

        rate_limiter.check_and_acquire("instagram")
        url = f"{self.BASE_URL}/me/messages"
        params = {"access_token": self.access_token}'''
new_ig = '''        self._validate_messaging_window(recipient_id, "instagram", last_interaction_time)

        token = access_token or self.access_token
        rate_limiter.check_and_acquire("instagram")
        url = f"{self.BASE_URL}/me/messages"
        params = {"access_token": token}'''
assert old_ig in src
src = src.replace(old_ig, new_ig, 1)
src = src.replace(
    '''        last_interaction_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Sends an Instagram Direct Message adhering to Instagram Business Messaging rules.
        """''',
    '''        last_interaction_time: Optional[datetime] = None,
        access_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sends an Instagram Direct Message adhering to Instagram Business Messaging rules.
        access_token: per-account token when provided (Wave 9.8), else legacy global.
        """''', 1)

open(p, "w", encoding="utf-8").write(src)
import ast; ast.parse(src)
print("client: resolve_page_token + per-token overrides in send paths")

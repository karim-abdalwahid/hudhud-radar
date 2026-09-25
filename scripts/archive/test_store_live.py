import sys, traceback
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()
from src.modules.connections.service import connection_service

OWNER = "8d0ab6c3-544d-4a14-84c9-d021acf26ddf"
try:
    r = connection_service.store(
        user_id=OWNER, platform="threads",
        access_token="TEST_TOKEN_SHOULD_NOT_THROW",
        account_id="123", account_name="@audit_test",
        scopes=["threads_basic"], token_expires_at="2026-11-10T00:00:00+00:00",
        metadata={"platform_user_id": "123"})
    print("store OK:", r)
except Exception:
    print("store THREW:")
    traceback.print_exc()

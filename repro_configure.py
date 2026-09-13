import asyncio
import sys
import traceback

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()
from src.modules.meta.routes import configure_meta_credentials, MetaConfigPayload


class FakeReq:
    cookies = {}


async def main():
    try:
        await configure_meta_credentials(MetaConfigPayload(), request=FakeReq())
        print("NO ERROR")
    except Exception:
        traceback.print_exc()

asyncio.run(main())

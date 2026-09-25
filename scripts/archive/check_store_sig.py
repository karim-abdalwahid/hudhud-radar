import inspect, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()
from src.modules.connections.service import connection_service
print("store signature:")
print(inspect.signature(connection_service.store))
print("\nstore source (head):")
src = inspect.getsource(connection_service.store)
print(src[:900])

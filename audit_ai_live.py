"""WS-F v2: AI live audit with the real API surface."""
import json, sys, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()

from src.ai.provider_manager import ai_provider_manager as ai
from src.agent.knowledge_base import knowledge_base as kb

print("=== 1. Providers ===")
try:
    provs = ai.list_providers()
    print(json.dumps(provs, ensure_ascii=False, indent=1)[:900])
except Exception as e:
    print("list_providers error:", str(e)[:200])

print("\n=== 2. Models ===")
try:
    models = ai.list_models()
    if isinstance(models, dict):
        models = models.get("models", models)
    print(json.dumps(models, ensure_ascii=False, default=str)[:600])
except Exception as e:
    print("list_models error:", str(e)[:200])

print("\n=== 3. Knowledge base (legacy global files) ===")
kb.reload()
docs = kb.list_documents()
print("documents:", len(docs), "->", [d.get("name") if isinstance(d, dict) else d for d in docs][:10])

print("\n=== 4. KB retrieval quality (sales context) ===")
try:
    ctx = kb.get_combined_context("بكام باقة ادارة الصفحات؟")
    print("context length:", len(ctx or ""))
    print("context sample:", (ctx or "")[:300].replace("\n", " | "))
except Exception as e:
    print("context error:", str(e)[:200])

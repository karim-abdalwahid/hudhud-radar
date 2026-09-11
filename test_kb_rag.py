"""Verify the agent's KB retrieval now works (db mode)."""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()
from src.agent.knowledge_base import knowledge_base as kb

kb.reload()
print("cache documents:", len(kb.knowledge_cache), "->", list(kb.knowledge_cache.keys()))

print("\n=== RAG retrieval test: 'بكام باقة ادارة الصفحات' ===")
try:
    chunks = kb.search_relevant_chunks("بكام باقة ادارة الصفحات؟", top_k=2)
    for c in chunks[:2]:
        print("  chunk:", str(c)[:180])
except Exception as e:
    print("search_relevant_chunks error:", str(e)[:200])

try:
    ctx = kb.get_combined_context()
    print("\ncombined context length:", len(ctx or ""))
    print("contains pricing info:", "جنيه" in (ctx or "") or "EGP" in (ctx or "") or "باقة" in (ctx or ""))
except Exception as e:
    print("combined context error:", str(e)[:200])

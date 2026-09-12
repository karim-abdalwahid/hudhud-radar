"""Phase A: enumerate ALL app routes; classify each endpoint's data source by
tracing its handler chain (static call-graph heuristics over module sources)."""
import json
import re
import sys
import inspect
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()

from src.main import app

routes = []
for r in app.routes:
    methods = getattr(r, "methods", None)
    path = getattr(r, "path", "")
    if methods and str(path).startswith(("/api", "/webhooks", "/auth")):
        routes.append((sorted(methods - {"HEAD", "OPTIONS"}), path, getattr(r, "endpoint", None)))

# gather all source text for heuristics
SOURCE = ""
for f in Path("src").rglob("*.py"):
    try:
        SOURCE += f.read_text(encoding="utf-8", errors="replace")
    except Exception:
        pass

MARKERS = {
    "GRAPH": re.compile(r"(graph\.facebook\.com|graph\.threads\.net|META_GRAPH_API_BASE_URL|THREADS_BASE_URL|self\.BASE_URL|meta_client|meta_publisher|threads_publisher|meta_token_manager|meta_insights|marketing_leads|meta_feed_sync|meta_crawler|httpx\.(get|post|AsyncClient))"),
    "AI": re.compile(r"(ai_provider_manager|conversation_engine|content_engine|generate_response|provider\.|llm)", re.I),
    "DB": re.compile(r"(supabase_db|db\.(select|insert|update|delete|upsert|get_setting))"),
}

rows = []
for methods, path, endpoint in sorted(routes, key=lambda x: x[1]):
    name = getattr(endpoint, "__name__", "?")
    mod = inspect.getmodule(endpoint)
    modfile = mod.__file__ if mod else "?"
    src = ""
    try:
        src = inspect.getsource(endpoint)
    except Exception:
        pass
    # include called helpers source via naive scan of identifiers in whole-file
    file_src = Path(modfile).read_text(encoding="utf-8", errors="replace") if modfile != "?" else ""
    body = src + file_src[:0]
    # trace: does the handler reference real-API singletons (from context imports)?
    used_real = bool(MARKERS["GRAPH"].search(src))
    used_ai = bool(MARKERS["AI"].search(src))
    used_db = bool(MARKERS["DB"].search(src))
    # fall back: module-level (endpoints often thin wrappers over services imported in context)
    if not (used_real or used_ai or used_db):
        used_real = bool(MARKERS["GRAPH"].search(file_src)) and bool(re.search(r"(meta|graph|threads|publisher|crawler|insights)", name + path, re.I))
    kind = "REAL-API" if used_real else ("AI" if used_ai else ("DB" if used_db else "STATIC?"))
    rows.append((methods[0] if methods else "?", path, kind, name))

print(f"{'METHOD':<7} {'PATH':<48} {'SOURCE':<10} HANDLER")
for m, p, k, n in rows:
    flag = " ⚠️" if k == "STATIC?" else ""
    print(f"{m:<7} {p:<48} {k:<10} {n}{flag}")

statics = [r for r in rows if r[2] == "STATIC?"]
print(f"\nTOTAL API routes: {len(rows)} | flagged for manual inspection: {len(statics)}")

"""Wire real per-user knowledge persistence (Phase C fix):
crawler/analyzer writes must reach kb_documents with the operating user."""
import ast
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 1. hybrid manager: user_id on save_document
p = "src/agent/knowledge_base.py"
src = open(p, encoding="utf-8").read()
old = '''    def save_document(self, filename: str, content: str) -> Dict[str, Any]:
        """Saves or edits a document (DB mode chunks+embeds; file mode writes)."""
        if self._mode == "db":
            try:
                from src.knowledge.db_knowledge_base import db_knowledge_base
                res = db_knowledge_base.save_document(filename, content)'''
new = '''    def save_document(self, filename: str, content: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Saves or edits a document (DB mode chunks+embeds with owner stamp; file mode writes)."""
        if self._mode == "db":
            try:
                from src.knowledge.db_knowledge_base import db_knowledge_base
                res = db_knowledge_base.save_document(filename, content, user_id=user_id)'''
assert old in src
src = src.replace(old, new, 1)
open(p, "w", encoding="utf-8").write(src)
ast.parse(src)
print("1. hybrid save_document(user_id) OK")

# 2. crawler: _persist_doc + thread user_id through synthesize_and_save
p = "src/knowledge/meta_crawler.py"
src = open(p, encoding="utf-8").read()
old_sig = "    async def synthesize_and_save(self, raw_data: Dict[str, Any]) -> Dict[str, str]:"
new_sig = ("    def _persist_doc(self, name: str, content: str) -> None:\n"
           "        \"\"\"Route every knowledge write through the hybrid manager so DB mode\n"
           "        persists to kb_documents with the operating user (Phase C truth fix).\"\"\"\n"
           "        try:\n"
           "            from src.agent.knowledge_base import knowledge_base\n"
           "            knowledge_base.save_document(name, content, user_id=getattr(self, \"_user_id\", None))\n"
           "        except Exception as e:\n"
           "            logger.warning(f\"KB persist via manager failed for {name} ({e}); direct file write\")\n"
           "            (self.kb_dir / name).write_text(content, encoding=\"utf-8\")\n\n"
           "    async def synthesize_and_save(self, raw_data: Dict[str, Any], user_id: Optional[str] = None) -> Dict[str, str]:")
assert old_sig in src
src = src.replace(old_sig, new_sig, 1)
src = src.replace("        \"\"\"\n        Processes extracted social content",
                  "        self._user_id = user_id\n        \"\"\"\n        Processes extracted social content", 1)
pat = re.compile(r'\(self\.kb_dir / "([\w.\-]+)")\.write_text\((.*), encoding="utf-8"\)')
src, n = pat.subn(lambda m: f'self._persist_doc("{m.group(1)}", {m.group(2)})', src)
open(p, "w", encoding="utf-8").write(src)
ast.parse(src)
print(f"2. crawler _persist_doc wired ({n} writes converted)")

# 3. analyzer: user_id pass-through
p = "src/knowledge/meta_analyzer.py"
src = open(p, encoding="utf-8").read()
src = src.replace("    async def analyze_recent(self, limit: int = 10) -> Dict[str, Any]:",
                  "    async def analyze_recent(self, limit: int = 10, user_id: Optional[str] = None) -> Dict[str, Any]:", 1)
i = src.find("db_knowledge_base.save_document(")
assert i > 0
end = src.find(")", i)
call = src[i:end+1]
if "user_id=" not in call:
    call2 = call.rstrip(")") + ", user_id=user_id)" if "\n" not in call else None
    if call2:
        src = src.replace(call, call2, 1)
open(p, "w", encoding="utf-8").write(src)
ast.parse(src)
print("3. analyzer user_id wired")

# 4. routes: pass session user into sync/analyze
p = "src/modules/knowledge/routes.py"
src = open(p, encoding="utf-8").read()
src = src.replace("    result = await meta_posts_analyzer.analyze_recent(limit=limit)",
                  "    result = await meta_posts_analyzer.analyze_recent(limit=limit, user_id=_session_user(request))", 1)
src = src.replace('''async def sync_knowledge_from_meta():
    """Scrapes historical Facebook/Instagram posts, reels, and comments and synthesizes business knowledge."""
    raw_data = await meta_crawler.fetch_all_historical_content()
    res = await knowledge_synthesizer.synthesize_and_save(raw_data)
    return res''',
                  '''async def sync_knowledge_from_meta(request: Request):
    """Scrapes historical Facebook/Instagram posts, reels, and comments and synthesizes business knowledge."""
    raw_data = await meta_crawler.fetch_all_historical_content()
    res = await knowledge_synthesizer.synthesize_and_save(raw_data, user_id=_session_user(request))
    return res''', 1)
open(p, "w", encoding="utf-8").write(src)
ast.parse(src)
print("4. routes wired to session user")

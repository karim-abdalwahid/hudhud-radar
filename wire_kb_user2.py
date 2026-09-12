"""Steps 2-4 of the KB user wiring (fixed regex), idempotent."""
import ast
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 2. crawler
p = "src/knowledge/meta_crawler.py"
src = open(p, encoding="utf-8").read()
if "_persist_doc" not in src:
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
    pat = re.compile(r'\(self\.kb_dir / "([\w.\-]+)"\)\.write_text\((.*), encoding="utf-8"\)')
    src, n = pat.subn(lambda m: f'self._persist_doc("{m.group(1)}", {m.group(2)})', src)
    print(f"   writes converted: {n}")
    open(p, "w", encoding="utf-8").write(src)
    ast.parse(src)
else:
    print("2. crawler already wired")

# 3. analyzer
p = "src/knowledge/meta_analyzer.py"
src = open(p, encoding="utf-8").read()
if "user_id=user_id" not in src and "def analyze_recent(self, limit: int = 10) -> Dict[str, Any]:" in src:
    src = src.replace("    async def analyze_recent(self, limit: int = 10) -> Dict[str, Any]:",
                      "    async def analyze_recent(self, limit: int = 10, user_id: Optional[str] = None) -> Dict[str, Any]:", 1)
    i = src.find("db_knowledge_base.save_document(")
    j = src.find(")", i)
    call = src[i:j + 1]
    print("   analyzer call:", call.replace("\n", " ")[:150])
    if "user_id" not in call:
        newcall = call[:-1].rstrip() + ("" if call[:-1].rstrip().endswith(",") else ",") + " user_id=user_id)"
        src = src[:i] + newcall + src[j + 1:]
    open(p, "w", encoding="utf-8").write(src)
    ast.parse(src)
else:
    print("3. analyzer already wired / unknown shape")

# 4. routes
p = "src/modules/knowledge/routes.py"
src = open(p, encoding="utf-8").read()
if "analyze_recent(limit=limit, user_id=" not in src:
    src = src.replace("    result = await meta_posts_analyzer.analyze_recent(limit=limit)",
                      "    result = await meta_posts_analyzer.analyze_recent(limit=limit, user_id=_session_user(request))", 1)
if "async def sync_knowledge_from_meta():" in src:
    src = src.replace("async def sync_knowledge_from_meta():",
                      "async def sync_knowledge_from_meta(request: Request):", 1)
    src = src.replace("res = await knowledge_synthesizer.synthesize_and_save(raw_data)",
                      "res = await knowledge_synthesizer.synthesize_and_save(raw_data, user_id=_session_user(request))", 1)
open(p, "w", encoding="utf-8").write(src)
ast.parse(src)
print("4. routes wired")

# 5. cleanup ztest junk from DB + file
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()
from src.knowledge.db_knowledge_base import db_knowledge_base
ok = db_knowledge_base.delete_document("ztest_audit.md")
print("5. ztest_audit removed from DB:", ok)

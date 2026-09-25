"""Verify SERVER-RENDERED nav structure + body class (flash-free proof)."""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()
from src.main import app  # registers all modules
from src.core.modules import render_sidebar_nav, initial_body_class

nav = render_sidebar_nav("/users", True)
sec_dev = nav.split('dev-nav-section', 1)[-1]
print("server nav (admin, /users):")
print("  client-nav-section present:", 'client-nav-section' in nav)
print("  dev-nav-section present:", 'dev-nav-section' in nav)
import re
dev_links = re.findall(r'href="([^"]+)"', sec_dev)
print("  dev links:", dev_links)

print("\ninitial_body_class:")
print("  /users + admin + no cookie   ->", initial_body_class("/users", True))
print("  /users + admin + cookie=client ->", initial_body_class("/users", True, "client"))
print("  /inbox + admin + no cookie   ->", initial_body_class("/inbox", True))
print("  /users + regular user        ->", initial_body_class("/users", False))

nav_user = render_sidebar_nav("/inbox", False)
print("\nserver nav (regular user): admin links present:", "/users" in nav_user or "/templates" in nav_user)

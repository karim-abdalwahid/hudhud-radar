import subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = "src/templates/static/i18n.js"
src = open(p, encoding="utf-8").read()
en_anchor = '"nav.automations": "Automations & Workflows",'
ar_anchor = '"nav.automations": "الأتمتة وسير العمل",'
assert en_anchor in src and ar_anchor in src
src = src.replace(en_anchor,
    en_anchor + '\n        "mode.admin_only": "Developer Console",', 1)
src = src.replace(ar_anchor,
    ar_anchor + '\n        "mode.admin_only": "أدوات المطور والنظام",', 1)
open(p, "w", encoding="utf-8").write(src)
tf = tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8")
tf.write(src); tf.close()
r = subprocess.run(["node", "--check", tf.name], capture_output=True, text=True)
print("i18n.js:", "OK" if r.returncode == 0 else r.stderr[:200])

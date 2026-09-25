import re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

src = open("src/automations/service.py", encoding="utf-8").read()
# storage surface
for m in re.finditer(r"def (_load|_save|_load_supabase|_save_supabase|_load_file|_save_file)[^\n]*\n", src):
    line = src[:m.start()].count("\n") + 1
    print(f"line {line}: {m.group(0).strip()}")
print("---- model fields ----")
mod = open("src/automations/models.py", encoding="utf-8").read()
print(mod[:2600])

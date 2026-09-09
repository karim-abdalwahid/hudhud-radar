"""Scan all src modules for annotation names not imported (3.12 lazy-annotation trap).

Python 3.14 defers annotation evaluation (PEP 649) — local tests pass. Vercel
runs Python 3.12 where annotations evaluate at def-time → NameError at import.
This scanner finds Names used in annotations that aren't imported/defined.
"""
import ast
import builtins
import sys
from pathlib import Path

ROOT = Path("src")
STDLIB = set(sys.stdlib_module_names)
PROBLEM_MODULES = {"typing": {"Dict", "List", "Optional", "Any", "Tuple", "Callable", "Set"}}

problems = []

for p in sorted(ROOT.rglob("*.py")):
    try:
        tree = ast.parse(p.read_text(encoding="utf-8"))
    except SyntaxError:
        continue

    # collect names available in module scope
    available = set(dir(builtins))
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for a in node.names:
                available.add((a.asname or a.name).split(".")[0])
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    available.add(t.id)
        elif isinstance(node, ast.FunctionDef):
            available.add(node.name)
        elif isinstance(node, ast.ClassDef):
            available.add(node.name)

    def check_annotation(node):
        for sub in ast.walk(node):
            if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load):
                if sub.id not in available and sub.id not in STDLIB:
                    problems.append((str(p), sub.lineno, sub.id))

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = node.args
            all_args = list(args.args) + list(args.kwonlyargs)
            if args.vararg: all_args.append(args.vararg)
            if args.kwarg: all_args.append(args.kwarg)
            for a in all_args:
                if a.annotation: check_annotation(a.annotation)
            if node.returns: check_annotation(node.returns)

if problems:
    print(f"FOUND {len(problems)} annotation NameErrors (would crash on py3.12):")
    for f, ln, name in sorted(set(problems)):
        print(f"  {f}:{ln} → '{name}'")
else:
    print("CLEAN — no lazy-annotation traps found")

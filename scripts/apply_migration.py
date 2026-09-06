"""Apply a migration SQL file via Supabase Management API (statement splitter
is semicolon-based but respects dollar-quoted blocks and comments)."""
import re
import sys

import httpx

REF = "yncxwcvxssvnjffrvxib"


def split_statements(sql: str):
    """Splits SQL into statements, respecting $$ blocks and single quotes."""
    stmts = []
    buf = []
    in_dollar = False
    in_quote = False
    i = 0
    while i < len(sql):
        ch = sql[i]
        if not in_quote and sql.startswith("$$", i):
            in_dollar = not in_dollar
            buf.append("$$")
            i += 2
            continue
        if not in_dollar and ch == "'":
            # detect '' escape
            if in_quote and i + 1 < len(sql) and sql[i + 1] == "'":
                buf.append("''")
                i += 2
                continue
            in_quote = not in_quote
            buf.append(ch)
            i += 1
            continue
        if ch == ";" and not in_dollar and not in_quote:
            stmt = "".join(buf).strip()
            if stmt and not all(l.strip().startswith("--") or not l.strip() for l in stmt.splitlines()):
                stmts.append(stmt)
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    tail = "".join(buf).strip()
    if tail and not all(l.strip().startswith("--") or not l.strip() for l in tail.splitlines()):
        stmts.append(tail)
    # drop comment-only statements
    final = []
    for s in stmts:
        body = re.sub(r"--[^\n]*", "", s).strip()
        if body:
            final.append(s)
    return final


def main():
    path = sys.argv[1]
    token = sys.argv[2]
    sql = open(path, encoding="utf-8").read()
    statements = split_statements(sql)
    print(f"Applying {path}: {len(statements)} statements")
    ok = 0
    failed = []
    with httpx.Client(timeout=120) as client:
        for i, stmt in enumerate(statements, 1):
            first = [l for l in stmt.splitlines() if l.strip() and not l.strip().startswith("--")][0][:70]
            r = client.post(
                f"https://api.supabase.com/v1/projects/{REF}/database/query",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={"query": stmt + (";" if not stmt.rstrip().endswith(";") else "")},
            )
            if r.status_code in (200, 201):
                ok += 1
                print(f"  OK  {i:>2}. {first}")
            else:
                failed.append(first)
                print(f"FAIL  {i:>2}. {first}\n      {r.status_code} {r.text[:200]}")
    print(f"\nDone: {ok}/{len(statements)}")
    if failed:
        sys.exit(2)


if __name__ == "__main__":
    main()

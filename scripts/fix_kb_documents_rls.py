"""Fix kb_documents RLS (statement 9 of migration 003 was a comment-parsing casualty)."""
import httpx

TOKEN = "sbp_fc6bd018f43733b522f2326ecac2b54e8ce20e7f"
REF = "yncxwcvxssvnjffrvxib"
H = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

STATEMENTS = [
    "ALTER TABLE public.kb_documents ENABLE ROW LEVEL SECURITY;",
    'CREATE POLICY "Allow all access to service_role" ON public.kb_documents FOR ALL USING (true) WITH CHECK (true);',
    "REVOKE ALL ON public.kb_documents FROM anon;",
]


def main():
    with httpx.Client(timeout=60) as client:
        for stmt in STATEMENTS:
            r = client.post(
                f"https://api.supabase.com/v1/projects/{REF}/database/query",
                headers=H, json={"query": stmt},
            )
            print(f"{stmt[:55]}... -> {r.status_code} {r.text[:100] if r.text else ''}")
        # Verify
        q = "SELECT c.relname, c.relrowsecurity FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind='r' AND c.relname LIKE 'kb%' ORDER BY c.relname;"
        r = client.post(
            f"https://api.supabase.com/v1/projects/{REF}/database/query",
            headers=H, json={"query": q},
        )
        print("Verify:", r.json())


if __name__ == "__main__":
    main()

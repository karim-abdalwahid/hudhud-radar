"""
One-off migration runner for HudhudRadar (users + auth security tables).
Uses Supabase Management API with an owner-provided access token.
Run: python scripts/apply_migration_001.py
"""
import sys

import httpx

TOKEN = sys.argv[1] if len(sys.argv) > 1 else ""
REF = "yncxwcvxssvnjffrvxib"
H = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

STATEMENTS = [
    ("user_role_enum", "DO $$ BEGIN\n    CREATE TYPE user_role_enum AS ENUM ('admin', 'user');\nEXCEPTION\n    WHEN duplicate_object THEN null;\nEND $$;"),
    ("users table", """CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    phone VARCHAR(50),
    full_name VARCHAR(255),
    password_hash TEXT NOT NULL,
    role user_role_enum NOT NULL DEFAULT 'user',
    is_active BOOLEAN NOT NULL DEFAULT true,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);"""),
    ("users RLS enable", "ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;"),
    ("users RLS policy", """DO $$ BEGIN
    CREATE POLICY "Service role full access on users" ON public.users
        FOR ALL USING (auth.role() = 'service_role');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;"""),
    ("processed_events indexes", """CREATE INDEX IF NOT EXISTS idx_processed_events_key ON public.processed_events(event_key);
CREATE INDEX IF NOT EXISTS idx_processed_events_time ON public.processed_events(processed_at DESC);"""),
    ("processed_events RLS", """ALTER TABLE public.processed_events ENABLE ROW LEVEL SECURITY;
DO $$ BEGIN
    CREATE POLICY "Service role full access on processed_events" ON public.processed_events
        FOR ALL USING (auth.role() = 'service_role');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;"""),
    ("app_settings RLS", """ALTER TABLE public.app_settings ENABLE ROW LEVEL SECURITY;
DO $$ BEGIN
    CREATE POLICY "Service role full access on app_settings" ON public.app_settings
        FOR ALL USING (auth.role() = 'service_role');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;"""),
    ("content_posts RLS fix", """DROP POLICY IF EXISTS "Allow all access on content_posts" ON public.content_posts;
DO $$ BEGIN
    CREATE POLICY "Service role full access on content_posts" ON public.content_posts
        FOR ALL USING (auth.role() = 'service_role');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;"""),
    ("users updated_at trigger", """DROP TRIGGER IF EXISTS trg_users_updated_at ON public.users;
CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON public.users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();"""),
    ("leads.human_takeover comment", """COMMENT ON COLUMN public.leads.human_takeover IS 'When true, the AI agent pauses automatic replies for this lead (Human Takeover).';"""),
    ("users table comment", """COMMENT ON TABLE public.users IS 'Application users: admin (owner) and future SaaS customers. Phone captured at signup per owner requirement.';"""),
]


def main():
    if not TOKEN:
        print("Usage: python scripts/apply_migration_001.py <SUPABASE_ACCESS_TOKEN>")
        sys.exit(1)
    ok = 0
    failed = []
    with httpx.Client(timeout=90) as client:
        for name, query in STATEMENTS:
            r = client.post(
                f"https://api.supabase.com/v1/projects/{REF}/database/query",
                headers=H,
                json={"query": query},
            )
            if r.status_code in (200, 201):
                ok += 1
                print(f"  OK  {name}")
            else:
                failed.append(name)
                print(f"FAIL  {name}: {r.status_code} {r.text[:200]}")
    print(f"\nDone: {ok}/{len(STATEMENTS)} succeeded")
    if failed:
        print("Failed:", ", ".join(failed))
        sys.exit(2)


if __name__ == "__main__":
    main()

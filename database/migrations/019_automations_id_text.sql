-- Migration 019 (Wave 9.8): automations_workflows id is TEXT (the model uses
-- "wf_<hex8>" string ids; the table was created with a UUID PK).
-- The table is empty (created same day, service not yet writing) — safe conversion.

ALTER TABLE public.automations_workflows
    ALTER COLUMN id TYPE TEXT USING id::text;

ALTER TABLE public.automations_workflows
    ALTER COLUMN id SET DEFAULT '';

-- Migration 015: add 'threads' to lead_source_enum.
-- FINDING (audit 2026-09-11): leads.source is a Postgres ENUM missing the
-- 'threads' value added in code (PlatformSource.THREADS). Any Threads reply
-- captured by the bridge failed with 22P02 invalid input value.
-- NOTE: ALTER TYPE ... ADD VALUE runs inside a transaction in Postgres 12+;
-- executed standalone via management API.

ALTER TYPE public.lead_source_enum ADD VALUE IF NOT EXISTS 'threads' AFTER 'instagram';

-- Migration 020 (truth-audit Layer 3): platform_enum was missing the
-- PlatformSource members 'manual'/'other'. messages.platform and
-- activity_logs.platform use this enum with PlatformSource values, so a lead
-- captured via those sources would crash its message insert (same class as the
-- earlier 'threads' bug). Close it for every reachable member.

ALTER TYPE public.platform_enum ADD VALUE IF NOT EXISTS 'manual' AFTER 'instagram';
ALTER TYPE public.platform_enum ADD VALUE IF NOT EXISTS 'other' AFTER 'manual';

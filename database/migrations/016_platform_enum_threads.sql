-- Migration 016: add 'threads' to platform_enum (serves messages.platform,
-- activity_logs.platform, campaigns.platform, page_performance_metrics.platform).
-- FINDING (audit 2026-09-11): platform_enum missing 'threads' — Threads reply
-- capture failed on messages insert with 22P02.

ALTER TYPE public.platform_enum ADD VALUE IF NOT EXISTS 'threads' AFTER 'instagram';

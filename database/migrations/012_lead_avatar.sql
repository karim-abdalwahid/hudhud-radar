-- Migration 012: lead avatar_url — real customer photo from Messenger/Instagram Profile API.
-- Enables the inbox to render the customer's actual profile picture (Zero-Fabrication:
-- the URL only ever comes from the official Graph API response).

ALTER TABLE public.leads ADD COLUMN IF NOT EXISTS avatar_url TEXT;

-- Migration 024: Coupons may reference a real Polar discount (H1 audit fix).
-- Wire: coupons.polar_discount_id → billing quote.coupon_polar_id →
--       Polar checkout discount_id (only when a real id exists).
-- Until a coupon carries a polar discount id, its displayed discount is
-- FAIL-CLOSED at checkout (RuntimeError) instead of silently charging full price.

ALTER TABLE public.coupons
    ADD COLUMN IF NOT EXISTS polar_discount_id VARCHAR(80);

-- Note: coupon_redemptions stays untouched — the column is nullable on purpose,
-- so existing coupons keep working for redemption bookkeeping while any
-- discount claim requires an explicit Polar discount reference.
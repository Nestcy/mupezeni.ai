-- ============================================================================
-- Migration 003 (REPAIRED): Phase 9 Commerce Completion Layer
-- Replaces the original 003. Fixes:
--   * `customers` did not exist, so every FK to it failed
--   * `deliveries` and `payments` already exist from 002 with a different
--     shape, so CREATE TABLE IF NOT EXISTS silently skipped them and the
--     following indexes failed. They are now ALTERed into the Phase 9 shape.
-- Safe to re-run.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 0. Customers (end-customers of a business; the CRM root)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    external_customer_id VARCHAR(255),          -- id in Shopify / WooCommerce / CSV
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    display_name VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(50),
    country VARCHAR(2),
    status VARCHAR(30) NOT NULL DEFAULT 'active',   -- active, blocked, archived
    first_seen_at TIMESTAMPTZ DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_customers_business ON customers(business_id);
CREATE INDEX IF NOT EXISTS idx_customers_biz_phone ON customers(business_id, phone) WHERE phone IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_customers_biz_email ON customers(business_id, lower(email)) WHERE email IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_customers_biz_external
    ON customers(business_id, external_customer_id) WHERE external_customer_id IS NOT NULL;

-- ----------------------------------------------------------------------------
-- 1. Customer addresses
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS customer_addresses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    label VARCHAR(50) DEFAULT 'Home',
    recipient_name VARCHAR(255),
    phone VARCHAR(50),
    address_line_1 TEXT NOT NULL,
    address_line_2 TEXT,
    city VARCHAR(100) NOT NULL,
    region VARCHAR(100),
    country VARCHAR(2) NOT NULL DEFAULT 'ZM',
    postal_code VARCHAR(20),
    delivery_notes TEXT,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_customer_addresses_biz_cust ON customer_addresses(business_id, customer_id);
-- at most one default address per customer
CREATE UNIQUE INDEX IF NOT EXISTS uq_customer_addresses_one_default
    ON customer_addresses(customer_id) WHERE is_default;

-- ----------------------------------------------------------------------------
-- 2. Checkout sessions
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS checkout_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    cart_id UUID NOT NULL REFERENCES carts(id) ON DELETE CASCADE,
    currency VARCHAR(3) NOT NULL DEFAULT 'ZMW',
    subtotal BIGINT NOT NULL DEFAULT 0,
    discount_total BIGINT NOT NULL DEFAULT 0,
    shipping_total BIGINT NOT NULL DEFAULT 0,
    tax_total BIGINT NOT NULL DEFAULT 0,
    fee_total BIGINT NOT NULL DEFAULT 0,
    grand_total BIGINT NOT NULL DEFAULT 0,
    status VARCHAR(30) NOT NULL DEFAULT 'created',
    idempotency_key VARCHAR(255),
    delivery_address_id UUID REFERENCES customer_addresses(id) ON DELETE SET NULL,
    shipping_address JSONB,                      -- snapshot taken at checkout
    order_id UUID REFERENCES orders(id) ON DELETE SET NULL,
    expires_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_checkout_biz_idempotency UNIQUE (business_id, idempotency_key),
    CONSTRAINT ck_checkout_money_nonneg CHECK (
        subtotal >= 0 AND discount_total >= 0 AND shipping_total >= 0
        AND tax_total >= 0 AND fee_total >= 0 AND grand_total >= 0
    )
);

CREATE INDEX IF NOT EXISTS idx_checkout_sessions_biz ON checkout_sessions(business_id);
CREATE INDEX IF NOT EXISTS idx_checkout_sessions_cart ON checkout_sessions(cart_id);
CREATE INDEX IF NOT EXISTS idx_checkout_sessions_customer ON checkout_sessions(customer_id);
-- one checkout resolves to at most one order
CREATE UNIQUE INDEX IF NOT EXISTS uq_checkout_one_order
    ON checkout_sessions(order_id) WHERE order_id IS NOT NULL;

-- ----------------------------------------------------------------------------
-- 3. Payments: ALTER the 002 table into the Phase 9 shape (money in minor units)
-- ----------------------------------------------------------------------------
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_schema = 'public' AND table_name = 'payments' AND column_name = 'amount') THEN
        ALTER TABLE payments RENAME COLUMN amount TO amount_minor;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_schema = 'public' AND table_name = 'payments' AND column_name = 'external_reference') THEN
        ALTER TABLE payments RENAME COLUMN external_reference TO provider_payment_id;
    END IF;
END $$;

ALTER TABLE payments ADD COLUMN IF NOT EXISTS amount_minor BIGINT NOT NULL DEFAULT 0;
ALTER TABLE payments ALTER COLUMN amount_minor TYPE BIGINT;
ALTER TABLE payments ADD COLUMN IF NOT EXISTS provider_payment_id VARCHAR(255);
ALTER TABLE payments ADD COLUMN IF NOT EXISTS business_id UUID REFERENCES businesses(id) ON DELETE CASCADE;
ALTER TABLE payments ADD COLUMN IF NOT EXISTS checkout_id UUID REFERENCES checkout_sessions(id) ON DELETE SET NULL;
ALTER TABLE payments ADD COLUMN IF NOT EXISTS customer_id UUID REFERENCES customers(id) ON DELETE SET NULL;
ALTER TABLE payments ADD COLUMN IF NOT EXISTS payment_method_type VARCHAR(50);
ALTER TABLE payments ALTER COLUMN currency SET DEFAULT 'ZMW';

-- backfill tenant key from the order, then enforce it
UPDATE payments p
   SET business_id = s.business_id
  FROM orders o JOIN stores s ON s.id = o.store_id
 WHERE p.order_id = o.id AND p.business_id IS NULL;
-- (orders.business_id is added in 004; payments are backfilled via stores here)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM payments WHERE business_id IS NULL) THEN
        ALTER TABLE payments ALTER COLUMN business_id SET NOT NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_payments_biz ON payments(business_id);
CREATE INDEX IF NOT EXISTS idx_payments_checkout ON payments(checkout_id);
-- a provider payment id can only be recorded once
CREATE UNIQUE INDEX IF NOT EXISTS uq_payments_provider_payment
    ON payments(provider, provider_payment_id) WHERE provider_payment_id IS NOT NULL;

-- ----------------------------------------------------------------------------
-- 4. Payment events (webhook audit + idempotency)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS payment_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    payment_id UUID REFERENCES payments(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL,
    external_event_id VARCHAR(255) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    payload JSONB DEFAULT '{}'::jsonb,
    processed_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_payment_event_provider_evt UNIQUE (provider, external_event_id)
);

CREATE INDEX IF NOT EXISTS idx_payment_events_biz ON payment_events(business_id);
CREATE INDEX IF NOT EXISTS idx_payment_events_payment ON payment_events(payment_id);

-- ----------------------------------------------------------------------------
-- 5. Fulfillments
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fulfillments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    status VARCHAR(30) NOT NULL DEFAULT 'unfulfilled',
    items JSONB NOT NULL DEFAULT '[]'::jsonb,
    tracking_number VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fulfillments_biz_order ON fulfillments(business_id, order_id);

-- ----------------------------------------------------------------------------
-- 6. Deliveries: ALTER the 002 table into the Phase 9 shape
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS deliveries (   -- no-op when 002 has run
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_schema='public' AND table_name='deliveries' AND column_name='external_reference') THEN
        ALTER TABLE deliveries RENAME COLUMN external_reference TO provider_delivery_id;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_schema='public' AND table_name='deliveries' AND column_name='estimated_delivery') THEN
        ALTER TABLE deliveries RENAME COLUMN estimated_delivery TO estimated_delivery_at;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_schema='public' AND table_name='deliveries' AND column_name='delivered_at') THEN
        ALTER TABLE deliveries RENAME COLUMN delivered_at TO actual_delivery_at;
    END IF;
END $$;

ALTER TABLE deliveries ADD COLUMN IF NOT EXISTS business_id UUID REFERENCES businesses(id) ON DELETE CASCADE;
ALTER TABLE deliveries ADD COLUMN IF NOT EXISTS provider VARCHAR(50);
ALTER TABLE deliveries ADD COLUMN IF NOT EXISTS provider_delivery_id VARCHAR(255);
ALTER TABLE deliveries ADD COLUMN IF NOT EXISTS delivery_mode VARCHAR(30) NOT NULL DEFAULT 'external_provider';
ALTER TABLE deliveries ADD COLUMN IF NOT EXISTS status VARCHAR(30) NOT NULL DEFAULT 'pending';
ALTER TABLE deliveries ADD COLUMN IF NOT EXISTS tracking_number VARCHAR(100);
ALTER TABLE deliveries ADD COLUMN IF NOT EXISTS tracking_url TEXT;
ALTER TABLE deliveries ADD COLUMN IF NOT EXISTS pickup_address JSONB;
ALTER TABLE deliveries ADD COLUMN IF NOT EXISTS delivery_address JSONB;
ALTER TABLE deliveries ADD COLUMN IF NOT EXISTS estimated_delivery_at TIMESTAMPTZ;
ALTER TABLE deliveries ADD COLUMN IF NOT EXISTS actual_delivery_at TIMESTAMPTZ;
ALTER TABLE deliveries ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb;

UPDATE deliveries d
   SET business_id = s.business_id
  FROM orders o JOIN stores s ON s.id = o.store_id
 WHERE d.order_id = o.id AND d.business_id IS NULL;
UPDATE deliveries SET provider = 'manual' WHERE provider IS NULL;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM deliveries WHERE business_id IS NULL) THEN
        ALTER TABLE deliveries ALTER COLUMN business_id SET NOT NULL;
    END IF;
    ALTER TABLE deliveries ALTER COLUMN provider SET NOT NULL;
END $$;

CREATE INDEX IF NOT EXISTS idx_deliveries_biz_order ON deliveries(business_id, order_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_delivery_provider_id
    ON deliveries(provider, provider_delivery_id) WHERE provider_delivery_id IS NOT NULL;

-- ----------------------------------------------------------------------------
-- 7. Delivery events
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS delivery_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    delivery_id UUID NOT NULL REFERENCES deliveries(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL,
    external_event_id VARCHAR(255),
    status VARCHAR(30) NOT NULL,
    location VARCHAR(255),
    description TEXT,
    payload JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_delivery_events_deliv ON delivery_events(delivery_id);
CREATE INDEX IF NOT EXISTS idx_delivery_events_biz ON delivery_events(business_id);
-- duplicate delivery webhooks are ignored
CREATE UNIQUE INDEX IF NOT EXISTS uq_delivery_events_provider_evt
    ON delivery_events(provider, external_event_id) WHERE external_event_id IS NOT NULL;

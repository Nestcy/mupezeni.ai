-- ============================================================================
-- Migration 004: schema alignment, inventory safety, capability audit, RLS
--
-- What this does
--   1. Shared helpers (updated_at trigger, membership checks for RLS)
--   2. Aligns tables with what the Python code reads/writes
--      (products.slug/base_price, product_variants.sku/price_override, ...)
--   3. Adds tenant keys (business_id / customer_id) to carts, orders
--   4. Moves money columns to BIGINT minor units; default currency -> ZMW
--   5. Inventory: constraints + atomic reserve / release / commit functions
--   6. capability_executions + capability_approval_requests (used by
--      capabilities/runtime.py)
--   7. Enables RLS on every table that was missing it
--
-- RLS stance: every business table is readable by members of that business.
-- All writes are expected to go through the backend with the service-role key
-- (which bypasses RLS). No client-side write policies are added here.
-- Safe to re-run.
-- ============================================================================

-- ============================================================================
-- 1. HELPERS
-- ============================================================================
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END $$;

-- Attaches the updated_at trigger to every public table that has the column.
CREATE OR REPLACE FUNCTION apply_updated_at_triggers() RETURNS void
LANGUAGE plpgsql AS $$
DECLARE r record;
BEGIN
    FOR r IN
        SELECT c.table_name
          FROM information_schema.columns c
          JOIN information_schema.tables t
            ON t.table_schema = c.table_schema AND t.table_name = c.table_name
           AND t.table_type = 'BASE TABLE'
         WHERE c.table_schema = 'public' AND c.column_name = 'updated_at'
    LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS trg_set_updated_at ON public.%I', r.table_name);
        EXECUTE format('CREATE TRIGGER trg_set_updated_at BEFORE UPDATE ON public.%I '
                       'FOR EACH ROW EXECUTE FUNCTION set_updated_at()', r.table_name);
    END LOOP;
END $$;

-- Membership checks. SECURITY DEFINER avoids recursive RLS on business_members.
CREATE OR REPLACE FUNCTION is_business_member(p_business_id uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
    SELECT EXISTS (
        SELECT 1 FROM business_members
         WHERE business_id = p_business_id AND user_id = auth.uid()
    );
$$;

CREATE OR REPLACE FUNCTION has_business_role(p_business_id uuid, p_roles business_role[]) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
    SELECT EXISTS (
        SELECT 1 FROM business_members
         WHERE business_id = p_business_id AND user_id = auth.uid()
           AND role = ANY (p_roles)
    );
$$;

-- Enables RLS and adds a "members can SELECT" policy on a table with business_id.
CREATE OR REPLACE FUNCTION apply_member_select_policy(p_table text) RETURNS void
LANGUAGE plpgsql AS $$
BEGIN
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', p_table);
    EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', p_table || '_select_member', p_table);
    EXECUTE format('CREATE POLICY %I ON public.%I FOR SELECT USING (is_business_member(business_id))',
                   p_table || '_select_member', p_table);
END $$;

-- Fills business_id on insert so existing code that only sends store_id keeps working.
CREATE OR REPLACE FUNCTION fill_business_id_from_store() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.business_id IS NULL THEN
        SELECT business_id INTO NEW.business_id FROM stores WHERE id = NEW.store_id;
    END IF;
    RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION fill_business_id_from_order() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.business_id IS NULL THEN
        SELECT business_id INTO NEW.business_id FROM orders WHERE id = NEW.order_id;
    END IF;
    RETURN NEW;
END $$;

REVOKE ALL ON FUNCTION apply_updated_at_triggers() FROM PUBLIC;
REVOKE ALL ON FUNCTION apply_member_select_policy(text) FROM PUBLIC;

-- ============================================================================
-- 2. CATALOG ALIGNMENT (code uses slug, base_price, sku, price_override)
-- ============================================================================
ALTER TABLE products ADD COLUMN IF NOT EXISTS slug VARCHAR(255);
ALTER TABLE products ADD COLUMN IF NOT EXISTS base_price BIGINT NOT NULL DEFAULT 0;  -- minor units

UPDATE products SET base_price = ROUND(price * 100)::BIGINT
 WHERE price IS NOT NULL AND base_price = 0;
UPDATE products
   SET slug = trim(both '-' from lower(regexp_replace(name, '[^a-zA-Z0-9]+', '-', 'g'))) || '-' || substr(id::text, 1, 8)
 WHERE slug IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_products_catalog_slug ON products(catalog_id, slug) WHERE slug IS NOT NULL;
COMMENT ON COLUMN products.price IS 'DEPRECATED: use base_price (minor units).';

ALTER TABLE product_variants ADD COLUMN IF NOT EXISTS sku VARCHAR(100);
ALTER TABLE product_variants ADD COLUMN IF NOT EXISTS price_override BIGINT;          -- minor units
UPDATE product_variants SET sku = variant_sku WHERE sku IS NULL AND variant_sku IS NOT NULL;
UPDATE product_variants SET price_override = ROUND(price * 100)::BIGINT
 WHERE price IS NOT NULL AND price_override IS NULL;
CREATE INDEX IF NOT EXISTS idx_product_variants_sku_new ON product_variants(sku);
COMMENT ON COLUMN product_variants.price IS 'DEPRECATED: use price_override (minor units).';

-- Public store URLs: slugs must be unique; each store has one primary domain.
CREATE UNIQUE INDEX IF NOT EXISTS uq_stores_slug ON stores(lower(slug)) WHERE slug IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_domains_one_primary ON domains(store_id) WHERE is_primary;

-- ============================================================================
-- 3. CURRENCY DEFAULT (one default everywhere; change 'ZMW' here if needed)
-- ============================================================================
ALTER TABLE businesses       ALTER COLUMN currency SET DEFAULT 'ZMW';
ALTER TABLE products         ALTER COLUMN currency SET DEFAULT 'ZMW';
ALTER TABLE product_variants ALTER COLUMN currency SET DEFAULT 'ZMW';
ALTER TABLE carts            ALTER COLUMN currency SET DEFAULT 'ZMW';
ALTER TABLE orders           ALTER COLUMN currency SET DEFAULT 'ZMW';

-- ============================================================================
-- 4. CARTS (tenant key, customer link, abandonment tracking, BIGINT money)
-- ============================================================================
ALTER TABLE carts ADD COLUMN IF NOT EXISTS business_id UUID REFERENCES businesses(id) ON DELETE CASCADE;
ALTER TABLE carts ADD COLUMN IF NOT EXISTS customer_id UUID REFERENCES customers(id) ON DELETE SET NULL;
ALTER TABLE carts ADD COLUMN IF NOT EXISTS last_activity_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE carts ADD COLUMN IF NOT EXISTS abandoned_at TIMESTAMPTZ;
ALTER TABLE carts ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ;

UPDATE carts c SET business_id = s.business_id FROM stores s WHERE s.id = c.store_id AND c.business_id IS NULL;

DROP TRIGGER IF EXISTS trg_carts_fill_business ON carts;
CREATE TRIGGER trg_carts_fill_business BEFORE INSERT ON carts
    FOR EACH ROW EXECUTE FUNCTION fill_business_id_from_store();

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM carts WHERE business_id IS NULL) THEN
        ALTER TABLE carts ALTER COLUMN business_id SET NOT NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_carts_business ON carts(business_id);
CREATE INDEX IF NOT EXISTS idx_carts_customer ON carts(customer_id);
-- supports the abandoned-cart recovery scan
CREATE INDEX IF NOT EXISTS idx_carts_biz_status_activity ON carts(business_id, status, last_activity_at);

ALTER TABLE cart_items ALTER COLUMN unit_price TYPE BIGINT;
ALTER TABLE cart_items ALTER COLUMN subtotal   TYPE BIGINT;

-- ============================================================================
-- 5. ORDERS / ORDER ITEMS (tenant key, snapshots, BIGINT money)
-- ============================================================================
ALTER TABLE orders ADD COLUMN IF NOT EXISTS business_id UUID REFERENCES businesses(id) ON DELETE CASCADE;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS customer_id UUID REFERENCES customers(id) ON DELETE SET NULL;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS customer_name VARCHAR(255);
ALTER TABLE orders ADD COLUMN IF NOT EXISTS billing_address JSONB;          -- delivery_address (002) is the shipping snapshot
ALTER TABLE orders ADD COLUMN IF NOT EXISTS tax_total BIGINT NOT NULL DEFAULT 0;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS fee_total BIGINT NOT NULL DEFAULT 0;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS placed_at TIMESTAMPTZ;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS cancelled_at TIMESTAMPTZ;

ALTER TABLE orders ALTER COLUMN subtotal       TYPE BIGINT;
ALTER TABLE orders ALTER COLUMN discount_total TYPE BIGINT;
ALTER TABLE orders ALTER COLUMN delivery_fee   TYPE BIGINT;
ALTER TABLE orders ALTER COLUMN total          TYPE BIGINT;

UPDATE orders o SET business_id = s.business_id FROM stores s WHERE s.id = o.store_id AND o.business_id IS NULL;

DROP TRIGGER IF EXISTS trg_orders_fill_business ON orders;
CREATE TRIGGER trg_orders_fill_business BEFORE INSERT ON orders
    FOR EACH ROW EXECUTE FUNCTION fill_business_id_from_store();

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM orders WHERE business_id IS NULL) THEN
        ALTER TABLE orders ALTER COLUMN business_id SET NOT NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_orders_business ON orders(business_id);
CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_biz_created ON orders(business_id, created_at DESC);

ALTER TABLE order_items ADD COLUMN IF NOT EXISTS product_id UUID REFERENCES products(id) ON DELETE SET NULL;
ALTER TABLE order_items ADD COLUMN IF NOT EXISTS product_variant_id UUID REFERENCES product_variants(id) ON DELETE SET NULL;
ALTER TABLE order_items ADD COLUMN IF NOT EXISTS discount_total BIGINT NOT NULL DEFAULT 0;
ALTER TABLE order_items ADD COLUMN IF NOT EXISTS currency VARCHAR(3);
ALTER TABLE order_items ALTER COLUMN unit_price TYPE BIGINT;
ALTER TABLE order_items ALTER COLUMN subtotal   TYPE BIGINT;
CREATE INDEX IF NOT EXISTS idx_order_items_product ON order_items(product_id);

-- Money can never go negative.
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_orders_money_nonneg') THEN
        ALTER TABLE orders ADD CONSTRAINT ck_orders_money_nonneg CHECK (
            subtotal >= 0 AND discount_total >= 0 AND delivery_fee >= 0
            AND tax_total >= 0 AND fee_total >= 0 AND total >= 0);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_cart_items_money_nonneg') THEN
        ALTER TABLE cart_items ADD CONSTRAINT ck_cart_items_money_nonneg CHECK (unit_price >= 0 AND subtotal >= 0);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_order_items_money_nonneg') THEN
        ALTER TABLE order_items ADD CONSTRAINT ck_order_items_money_nonneg CHECK (unit_price >= 0 AND subtotal >= 0 AND discount_total >= 0);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_payments_amount_nonneg') THEN
        ALTER TABLE payments ADD CONSTRAINT ck_payments_amount_nonneg CHECK (amount_minor >= 0);
    END IF;
END $$;

-- Phase 9 tables written by backend code that may omit business_id
DROP TRIGGER IF EXISTS trg_payments_fill_business ON payments;
CREATE TRIGGER trg_payments_fill_business BEFORE INSERT ON payments
    FOR EACH ROW EXECUTE FUNCTION fill_business_id_from_order();
DROP TRIGGER IF EXISTS trg_deliveries_fill_business ON deliveries;
CREATE TRIGGER trg_deliveries_fill_business BEFORE INSERT ON deliveries
    FOR EACH ROW EXECUTE FUNCTION fill_business_id_from_order();
DROP TRIGGER IF EXISTS trg_fulfillments_fill_business ON fulfillments;
CREATE TRIGGER trg_fulfillments_fill_business BEFORE INSERT ON fulfillments
    FOR EACH ROW EXECUTE FUNCTION fill_business_id_from_order();

-- ============================================================================
-- 6. INVENTORY: constraints, derived columns, atomic reservation
-- ============================================================================
CREATE UNIQUE INDEX IF NOT EXISTS uq_inventory_variant ON inventory(product_variant_id);

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_inventory_quantities') THEN
        ALTER TABLE inventory ADD CONSTRAINT ck_inventory_quantities CHECK (
            quantity_on_hand >= 0 AND quantity_reserved >= 0 AND quantity_reserved <= quantity_on_hand);
    END IF;
END $$;

-- quantity_available and status are always derived, never trusted from the caller
CREATE OR REPLACE FUNCTION inventory_recompute() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    NEW.quantity_available := GREATEST(NEW.quantity_on_hand - NEW.quantity_reserved, 0);
    NEW.status := CASE
        WHEN NEW.quantity_available <= 0 THEN 'out_of_stock'
        WHEN NEW.quantity_available <= COALESCE(NEW.reorder_level, 0) THEN 'low_stock'
        ELSE 'in_stock' END;
    RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS trg_inventory_recompute ON inventory;
CREATE TRIGGER trg_inventory_recompute BEFORE INSERT OR UPDATE ON inventory
    FOR EACH ROW EXECUTE FUNCTION inventory_recompute();

CREATE TABLE IF NOT EXISTS inventory_movements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    product_variant_id UUID NOT NULL REFERENCES product_variants(id) ON DELETE CASCADE,
    movement_type VARCHAR(30) NOT NULL,   -- reserve, release, commit, restock, adjustment
    quantity INT NOT NULL,
    reference_type VARCHAR(50),           -- checkout, order, manual, import
    reference_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_inventory_movements_biz ON inventory_movements(business_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_inventory_movements_variant ON inventory_movements(product_variant_id);

-- Single-statement UPDATE: the row lock makes "two customers, last item" safe.
-- Returns FALSE (does not raise) when there is not enough stock.
CREATE OR REPLACE FUNCTION reserve_inventory(
    p_variant_id uuid, p_quantity int,
    p_reference_type text DEFAULT NULL, p_reference_id uuid DEFAULT NULL
) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE v_rows int; v_business uuid;
BEGIN
    IF p_quantity IS NULL OR p_quantity <= 0 THEN
        RAISE EXCEPTION 'quantity must be positive';
    END IF;
    UPDATE inventory
       SET quantity_reserved = quantity_reserved + p_quantity
     WHERE product_variant_id = p_variant_id
       AND quantity_on_hand - quantity_reserved >= p_quantity;
    GET DIAGNOSTICS v_rows = ROW_COUNT;
    IF v_rows = 0 THEN RETURN FALSE; END IF;

    SELECT s.business_id INTO v_business
      FROM product_variants v
      JOIN products p ON p.id = v.product_id
      JOIN catalogs c ON c.id = p.catalog_id
      JOIN stores s ON s.id = c.store_id
     WHERE v.id = p_variant_id;
    INSERT INTO inventory_movements(business_id, product_variant_id, movement_type, quantity, reference_type, reference_id)
    VALUES (v_business, p_variant_id, 'reserve', p_quantity, p_reference_type, p_reference_id);
    RETURN TRUE;
END $$;

CREATE OR REPLACE FUNCTION release_inventory(
    p_variant_id uuid, p_quantity int,
    p_reference_type text DEFAULT NULL, p_reference_id uuid DEFAULT NULL
) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE v_rows int; v_business uuid;
BEGIN
    IF p_quantity IS NULL OR p_quantity <= 0 THEN
        RAISE EXCEPTION 'quantity must be positive';
    END IF;
    UPDATE inventory
       SET quantity_reserved = quantity_reserved - p_quantity
     WHERE product_variant_id = p_variant_id AND quantity_reserved >= p_quantity;
    GET DIAGNOSTICS v_rows = ROW_COUNT;
    IF v_rows = 0 THEN RETURN FALSE; END IF;

    SELECT s.business_id INTO v_business
      FROM product_variants v JOIN products p ON p.id = v.product_id
      JOIN catalogs c ON c.id = p.catalog_id JOIN stores s ON s.id = c.store_id
     WHERE v.id = p_variant_id;
    INSERT INTO inventory_movements(business_id, product_variant_id, movement_type, quantity, reference_type, reference_id)
    VALUES (v_business, p_variant_id, 'release', p_quantity, p_reference_type, p_reference_id);
    RETURN TRUE;
END $$;

-- Converts a reservation into a real stock decrease (e.g. once paid / dispatched).
CREATE OR REPLACE FUNCTION commit_inventory(
    p_variant_id uuid, p_quantity int,
    p_reference_type text DEFAULT NULL, p_reference_id uuid DEFAULT NULL
) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE v_rows int; v_business uuid;
BEGIN
    IF p_quantity IS NULL OR p_quantity <= 0 THEN
        RAISE EXCEPTION 'quantity must be positive';
    END IF;
    UPDATE inventory
       SET quantity_on_hand = quantity_on_hand - p_quantity,
           quantity_reserved = quantity_reserved - p_quantity
     WHERE product_variant_id = p_variant_id AND quantity_reserved >= p_quantity;
    GET DIAGNOSTICS v_rows = ROW_COUNT;
    IF v_rows = 0 THEN RETURN FALSE; END IF;

    SELECT s.business_id INTO v_business
      FROM product_variants v JOIN products p ON p.id = v.product_id
      JOIN catalogs c ON c.id = p.catalog_id JOIN stores s ON s.id = c.store_id
     WHERE v.id = p_variant_id;
    INSERT INTO inventory_movements(business_id, product_variant_id, movement_type, quantity, reference_type, reference_id)
    VALUES (v_business, p_variant_id, 'commit', p_quantity, p_reference_type, p_reference_id);
    RETURN TRUE;
END $$;

-- Only the backend (service role) may move stock.
REVOKE ALL ON FUNCTION reserve_inventory(uuid, int, text, uuid) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION release_inventory(uuid, int, text, uuid) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION commit_inventory(uuid, int, text, uuid)  FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION reserve_inventory(uuid, int, text, uuid) TO service_role;
GRANT EXECUTE ON FUNCTION release_inventory(uuid, int, text, uuid) TO service_role;
GRANT EXECUTE ON FUNCTION commit_inventory(uuid, int, text, uuid)  TO service_role;

-- ============================================================================
-- 7. CAPABILITY AUDIT + APPROVALS (written by capabilities/runtime.py)
-- ============================================================================
CREATE TABLE IF NOT EXISTS capability_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id TEXT NOT NULL,
    business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    capability VARCHAR(150) NOT NULL,
    status VARCHAR(50) NOT NULL,
    provider VARCHAR(100),
    executed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_capability_executions_biz ON capability_executions(business_id, executed_at DESC);
CREATE INDEX IF NOT EXISTS idx_capability_executions_request ON capability_executions(request_id);

CREATE TABLE IF NOT EXISTS capability_approval_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    approval_id TEXT NOT NULL UNIQUE,
    request_id TEXT NOT NULL,
    business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    capability VARCHAR(150) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'pending',   -- pending, approved, rejected, expired, cancelled
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    decided_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    decided_at TIMESTAMPTZ,
    decision_comment TEXT,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_capability_approvals_biz_status ON capability_approval_requests(business_id, status);

-- ============================================================================
-- 8. ROW LEVEL SECURITY
-- ============================================================================
-- business_members: members can see their teammates (was: only own row).
DROP POLICY IF EXISTS "business_members_select_own" ON business_members;
DROP POLICY IF EXISTS "business_members_select_co_members" ON business_members;
CREATE POLICY "business_members_select_co_members" ON business_members
    FOR SELECT USING (is_business_member(business_id));

-- Tables with a direct business_id column
SELECT apply_member_select_policy(t) FROM unnest(ARRAY[
    'customers', 'customer_addresses', 'checkout_sessions', 'payments', 'payment_events',
    'fulfillments', 'deliveries', 'delivery_events', 'inventory_movements',
    'capability_executions', 'capability_approval_requests'
]) AS t;

-- Child tables without their own business_id
ALTER TABLE cart_items ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "cart_items_select_member" ON cart_items;
CREATE POLICY "cart_items_select_member" ON cart_items FOR SELECT USING (
    EXISTS (SELECT 1 FROM carts c WHERE c.id = cart_items.cart_id AND is_business_member(c.business_id)));

ALTER TABLE order_items ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "order_items_select_member" ON order_items;
CREATE POLICY "order_items_select_member" ON order_items FOR SELECT USING (
    EXISTS (SELECT 1 FROM orders o WHERE o.id = order_items.order_id AND is_business_member(o.business_id)));

-- Global reference tables: readable by any signed-in user, writable only by service role
ALTER TABLE connector_definitions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "connector_definitions_select_authenticated" ON connector_definitions;
CREATE POLICY "connector_definitions_select_authenticated" ON connector_definitions
    FOR SELECT TO authenticated USING (true);

ALTER TABLE connector_capabilities ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "connector_capabilities_select_authenticated" ON connector_capabilities;
CREATE POLICY "connector_capabilities_select_authenticated" ON connector_capabilities
    FOR SELECT TO authenticated USING (true);

-- ============================================================================
-- 9. updated_at triggers on every table that has the column
-- ============================================================================
SELECT apply_updated_at_triggers();

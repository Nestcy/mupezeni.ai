-- ============================================================================
-- PHASE 2: COMMERCE SYSTEM EXTENSIONS
-- ============================================================================
-- This migration extends the initial schema with commerce-specific tables
-- for stores, domains, catalogs, products, variants, inventory, carts, and orders.

-- ============================================================================
-- UPDATE STORES TABLE
-- ============================================================================
ALTER TABLE stores ADD COLUMN IF NOT EXISTS published_at TIMESTAMP WITH TIME ZONE;

-- ============================================================================
-- DOMAINS (already exists, ensure schema is correct)
-- ============================================================================
-- Already created in 001_initial_schema.sql with proper structure

-- ============================================================================
-- CARTS
-- ============================================================================
CREATE TABLE IF NOT EXISTS carts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    status VARCHAR(50) DEFAULT 'active', -- active, abandoned, converted, expired
    currency VARCHAR(3) DEFAULT 'USD',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_carts_store_id ON carts(store_id);
CREATE INDEX idx_carts_status ON carts(status);
CREATE INDEX idx_carts_created_at ON carts(created_at);

-- ============================================================================
-- CART ITEMS
-- ============================================================================
CREATE TABLE IF NOT EXISTS cart_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cart_id UUID NOT NULL REFERENCES carts(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    product_variant_id UUID REFERENCES product_variants(id) ON DELETE SET NULL,
    quantity INT NOT NULL DEFAULT 1 CHECK (quantity > 0),
    unit_price INT NOT NULL DEFAULT 0, -- minor units (e.g., cents)
    subtotal INT NOT NULL DEFAULT 0, -- quantity * unit_price
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_cart_items_cart_id ON cart_items(cart_id);
CREATE INDEX idx_cart_items_product_id ON cart_items(product_id);
CREATE INDEX idx_cart_items_product_variant_id ON cart_items(product_variant_id);

-- ============================================================================
-- ORDERS
-- ============================================================================
CREATE TABLE IF NOT EXISTS orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    order_number VARCHAR(50) NOT NULL UNIQUE, -- human-readable order ID
    status VARCHAR(50) DEFAULT 'pending', -- pending, confirmed, processing, ready, dispatched, completed, cancelled
    payment_status VARCHAR(50) DEFAULT 'pending', -- pending, paid, failed, refunded
    currency VARCHAR(3) DEFAULT 'USD',
    subtotal INT NOT NULL DEFAULT 0, -- minor units
    discount_total INT NOT NULL DEFAULT 0,
    delivery_fee INT NOT NULL DEFAULT 0,
    total INT NOT NULL DEFAULT 0,
    customer_email VARCHAR(255),
    customer_phone VARCHAR(20),
    delivery_address JSONB,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_orders_store_id ON orders(store_id);
CREATE INDEX idx_orders_order_number ON orders(order_number);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_payment_status ON orders(payment_status);
CREATE INDEX idx_orders_created_at ON orders(created_at);

-- ============================================================================
-- ORDER ITEMS
-- ============================================================================
CREATE TABLE IF NOT EXISTS order_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_name VARCHAR(255) NOT NULL, -- snapshot at order time
    product_sku VARCHAR(100) NOT NULL, -- snapshot at order time
    variant_attributes JSONB, -- snapshot at order time
    unit_price INT NOT NULL DEFAULT 0, -- minor units
    quantity INT NOT NULL DEFAULT 1 CHECK (quantity > 0),
    subtotal INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_order_items_order_id ON order_items(order_id);

-- ============================================================================
-- PAYMENTS (abstract for future integration)
-- ============================================================================
CREATE TABLE IF NOT EXISTS payments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    amount INT NOT NULL DEFAULT 0, -- minor units
    currency VARCHAR(3) DEFAULT 'USD',
    provider VARCHAR(100), -- mtn_momo, stripe, etc (future)
    external_reference VARCHAR(255), -- reference from external provider
    status VARCHAR(50) DEFAULT 'pending', -- pending, paid, failed, refunded
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_payments_order_id ON payments(order_id);
CREATE INDEX idx_payments_status ON payments(status);

-- ============================================================================
-- DELIVERIES (abstract for future integration)
-- ============================================================================
CREATE TABLE IF NOT EXISTS deliveries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    provider VARCHAR(100), -- yango, dhl, etc (future)
    external_reference VARCHAR(255),
    status VARCHAR(50) DEFAULT 'pending', -- pending, accepted, in_transit, delivered, failed, cancelled
    tracking_url TEXT,
    estimated_delivery TIMESTAMP WITH TIME ZONE,
    delivered_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_deliveries_order_id ON deliveries(order_id);
CREATE INDEX idx_deliveries_status ON deliveries(status);

-- ============================================================================
-- ENABLE RLS ON NEW COMMERCE TABLES
-- ============================================================================
ALTER TABLE carts ENABLE ROW LEVEL SECURITY;
ALTER TABLE cart_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE order_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE deliveries ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- RLS POLICIES FOR CARTS (access through store -> business membership)
-- ============================================================================
CREATE POLICY "carts_select_through_membership" ON carts
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM stores
            JOIN business_members ON business_members.business_id = stores.business_id
            WHERE carts.store_id = stores.id
            AND business_members.user_id = auth.uid()
        )
    );

-- ============================================================================
-- RLS POLICIES FOR ORDERS (access through store -> business membership)
-- ============================================================================
CREATE POLICY "orders_select_through_membership" ON orders
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM stores
            JOIN business_members ON business_members.business_id = stores.business_id
            WHERE orders.store_id = stores.id
            AND business_members.user_id = auth.uid()
        )
    );

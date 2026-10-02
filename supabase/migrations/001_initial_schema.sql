-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- PROFILES (linked to auth.users)
-- ============================================================================
CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    avatar_url TEXT,
    phone VARCHAR(20),
    timezone VARCHAR(50) DEFAULT 'UTC',
    language VARCHAR(10) DEFAULT 'en',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_profiles_user_id ON profiles(user_id);

-- ============================================================================
-- BUSINESSES
-- ============================================================================
CREATE TABLE IF NOT EXISTS businesses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    industry VARCHAR(100),
    country VARCHAR(2),
    city VARCHAR(255),
    currency VARCHAR(3) DEFAULT 'USD',
    phone VARCHAR(20),
    email VARCHAR(255),
    website VARCHAR(255),
    logo_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_businesses_created_at ON businesses(created_at);
CREATE INDEX idx_businesses_name ON businesses(name);

-- ============================================================================
-- BUSINESS MEMBERS (many-to-many with users)
-- ============================================================================
CREATE TYPE business_role AS ENUM ('owner', 'admin', 'member');

CREATE TABLE IF NOT EXISTS business_members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role business_role NOT NULL DEFAULT 'member',
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(business_id, user_id)
);

CREATE INDEX idx_business_members_business_id ON business_members(business_id);
CREATE INDEX idx_business_members_user_id ON business_members(user_id);
CREATE INDEX idx_business_members_role ON business_members(role);

-- ============================================================================
-- BRAND PROFILES
-- ============================================================================
CREATE TABLE IF NOT EXISTS brand_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    business_id UUID NOT NULL UNIQUE REFERENCES businesses(id) ON DELETE CASCADE,
    brand_name VARCHAR(255) NOT NULL,
    tone JSONB DEFAULT '["professional", "friendly"]'::jsonb,
    primary_color VARCHAR(7),
    secondary_color VARCHAR(7),
    accent_color VARCHAR(7),
    background_color VARCHAR(7),
    text_color VARCHAR(7),
    heading_font VARCHAR(100),
    body_font VARCHAR(100),
    visual_style VARCHAR(100),
    imagery_style VARCHAR(100),
    background_preference VARCHAR(100),
    marketing_guidelines TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_brand_profiles_business_id ON brand_profiles(business_id);

-- ============================================================================
-- BRAND ASSETS (Supabase Storage references)
-- ============================================================================
CREATE TABLE IF NOT EXISTS brand_assets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    brand_profile_id UUID NOT NULL REFERENCES brand_profiles(id) ON DELETE CASCADE,
    asset_type VARCHAR(50) NOT NULL, -- logo, banner, icon, etc
    asset_name VARCHAR(255),
    storage_path TEXT NOT NULL, -- path in Supabase Storage
    public_url TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_brand_assets_brand_profile_id ON brand_assets(brand_profile_id);
CREATE INDEX idx_brand_assets_asset_type ON brand_assets(asset_type);

-- ============================================================================
-- STORES
-- ============================================================================
CREATE TABLE IF NOT EXISTS stores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    slug VARCHAR(255),
    status VARCHAR(50) DEFAULT 'active',
    configuration JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_stores_business_id ON stores(business_id);
CREATE INDEX idx_stores_slug ON stores(slug);
CREATE INDEX idx_stores_status ON stores(status);

-- ============================================================================
-- DOMAINS
-- ============================================================================
CREATE TYPE domain_type AS ENUM ('mupezeni_subdomain', 'custom');

CREATE TABLE IF NOT EXISTS domains (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    domain VARCHAR(255) NOT NULL UNIQUE,
    domain_type domain_type NOT NULL,
    status VARCHAR(50) DEFAULT 'pending', -- pending, active, failed
    is_primary BOOLEAN DEFAULT FALSE,
    dns_records JSONB,
    verified_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_domains_store_id ON domains(store_id);
CREATE INDEX idx_domains_domain ON domains(domain);
CREATE INDEX idx_domains_status ON domains(status);

-- ============================================================================
-- CATALOGS
-- ============================================================================
CREATE TABLE IF NOT EXISTS catalogs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'active',
    configuration JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_catalogs_store_id ON catalogs(store_id);
CREATE INDEX idx_catalogs_status ON catalogs(status);

-- ============================================================================
-- PRODUCTS
-- ============================================================================
CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    catalog_id UUID NOT NULL REFERENCES catalogs(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    sku VARCHAR(100),
    category VARCHAR(100),
    price DECIMAL(12, 2),
    currency VARCHAR(3) DEFAULT 'USD',
    status VARCHAR(50) DEFAULT 'active',
    images JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_products_catalog_id ON products(catalog_id);
CREATE INDEX idx_products_sku ON products(sku);
CREATE INDEX idx_products_status ON products(status);
CREATE INDEX idx_products_category ON products(category);

-- ============================================================================
-- PRODUCT VARIANTS
-- ============================================================================
CREATE TABLE IF NOT EXISTS product_variants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    variant_name VARCHAR(255),
    variant_sku VARCHAR(100),
    price DECIMAL(12, 2),
    currency VARCHAR(3) DEFAULT 'USD',
    attributes JSONB DEFAULT '{}'::jsonb,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_product_variants_product_id ON product_variants(product_id);
CREATE INDEX idx_product_variants_sku ON product_variants(variant_sku);

-- ============================================================================
-- INVENTORY
-- ============================================================================
CREATE TABLE IF NOT EXISTS inventory (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_variant_id UUID NOT NULL REFERENCES product_variants(id) ON DELETE CASCADE,
    quantity_on_hand INT DEFAULT 0,
    quantity_reserved INT DEFAULT 0,
    quantity_available INT DEFAULT 0,
    reorder_level INT DEFAULT 10,
    status VARCHAR(50) DEFAULT 'in_stock', -- in_stock, low_stock, out_of_stock
    last_checked_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_inventory_product_variant_id ON inventory(product_variant_id);
CREATE INDEX idx_inventory_status ON inventory(status);

-- ============================================================================
-- CONNECTOR DEFINITIONS (platform-supported provider/capability combinations)
-- ============================================================================
CREATE TABLE IF NOT EXISTS connector_definitions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    capability VARCHAR(100) NOT NULL, -- catalog, messaging, ads, payments, delivery
    provider VARCHAR(100) NOT NULL, -- mupezeni, shopify, whatsapp, meta, etc
    display_name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'available', -- available, beta, deprecated
    documentation_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(capability, provider)
);

CREATE INDEX idx_connector_definitions_capability ON connector_definitions(capability);
CREATE INDEX idx_connector_definitions_provider ON connector_definitions(provider);

-- ============================================================================
-- BUSINESS CONNECTORS (which provider a business uses for a capability)
-- ============================================================================
CREATE TABLE IF NOT EXISTS business_connectors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    connector_definition_id UUID NOT NULL REFERENCES connector_definitions(id) ON DELETE RESTRICT,
    status VARCHAR(50) DEFAULT 'inactive', -- inactive, connecting, connected, failed
    configuration JSONB DEFAULT '{}'::jsonb,
    connected_at TIMESTAMP WITH TIME ZONE,
    last_health_check_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(business_id, connector_definition_id)
);

CREATE INDEX idx_business_connectors_business_id ON business_connectors(business_id);
CREATE INDEX idx_business_connectors_connector_definition_id ON business_connectors(connector_definition_id);
CREATE INDEX idx_business_connectors_status ON business_connectors(status);

-- ============================================================================
-- CONNECTOR CREDENTIALS
-- ============================================================================
CREATE TABLE IF NOT EXISTS connector_credentials (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    business_connector_id UUID NOT NULL REFERENCES business_connectors(id) ON DELETE CASCADE,
    credential_type VARCHAR(100) NOT NULL, -- api_key, oauth_token, webhook_secret, etc
    secret_reference TEXT, -- placeholder for secret vault integration
    status VARCHAR(50) DEFAULT 'active', -- active, expired, revoked
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_connector_credentials_business_connector_id ON connector_credentials(business_connector_id);
CREATE INDEX idx_connector_credentials_status ON connector_credentials(status);

-- ============================================================================
-- CONNECTOR CAPABILITIES (actions supported by a provider)
-- ============================================================================
CREATE TABLE IF NOT EXISTS connector_capabilities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    connector_definition_id UUID NOT NULL REFERENCES connector_definitions(id) ON DELETE CASCADE,
    action VARCHAR(100) NOT NULL, -- search_products, check_inventory, etc
    description TEXT,
    requires_authentication BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(connector_definition_id, action)
);

CREATE INDEX idx_connector_capabilities_connector_definition_id ON connector_capabilities(connector_definition_id);

-- ============================================================================
-- BUSINESS CONNECTOR PERMISSIONS
-- ============================================================================
CREATE TABLE IF NOT EXISTS business_connector_permissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    business_connector_id UUID NOT NULL REFERENCES business_connectors(id) ON DELETE CASCADE,
    action VARCHAR(100) NOT NULL,
    enabled BOOLEAN DEFAULT FALSE,
    requires_approval BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(business_connector_id, action)
);

CREATE INDEX idx_business_connector_permissions_business_connector_id ON business_connector_permissions(business_connector_id);

-- ============================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================================================

-- Enable RLS on business-related tables
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE businesses ENABLE ROW LEVEL SECURITY;
ALTER TABLE business_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE brand_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE brand_assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE stores ENABLE ROW LEVEL SECURITY;
ALTER TABLE domains ENABLE ROW LEVEL SECURITY;
ALTER TABLE catalogs ENABLE ROW LEVEL SECURITY;
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
ALTER TABLE product_variants ENABLE ROW LEVEL SECURITY;
ALTER TABLE inventory ENABLE ROW LEVEL SECURITY;
ALTER TABLE business_connectors ENABLE ROW LEVEL SECURITY;
ALTER TABLE connector_credentials ENABLE ROW LEVEL SECURITY;
ALTER TABLE business_connector_permissions ENABLE ROW LEVEL SECURITY;

-- PROFILES: Users can only view/update their own profile
CREATE POLICY "profiles_select_own" ON profiles
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "profiles_update_own" ON profiles
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "profiles_insert_own" ON profiles
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- BUSINESSES: Only accessible through business_members
CREATE POLICY "businesses_select_through_membership" ON businesses
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM business_members
            WHERE business_members.business_id = businesses.id
            AND business_members.user_id = auth.uid()
        )
    );

CREATE POLICY "businesses_update_as_admin" ON businesses
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM business_members
            WHERE business_members.business_id = businesses.id
            AND business_members.user_id = auth.uid()
            AND business_members.role IN ('owner', 'admin')
        )
    );

-- BUSINESS_MEMBERS: Users can view their own memberships
CREATE POLICY "business_members_select_own" ON business_members
    FOR SELECT USING (auth.uid() = user_id);

-- BRAND_PROFILES: Access through business membership
CREATE POLICY "brand_profiles_select_through_membership" ON brand_profiles
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM business_members
            WHERE business_members.business_id = brand_profiles.business_id
            AND business_members.user_id = auth.uid()
        )
    );

CREATE POLICY "brand_profiles_update_as_admin" ON brand_profiles
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM business_members
            WHERE business_members.business_id = brand_profiles.business_id
            AND business_members.user_id = auth.uid()
            AND business_members.role IN ('owner', 'admin')
        )
    );

-- BRAND_ASSETS: Access through brand_profiles
CREATE POLICY "brand_assets_select_through_membership" ON brand_assets
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM brand_profiles
            JOIN business_members ON business_members.business_id = brand_profiles.business_id
            WHERE brand_assets.brand_profile_id = brand_profiles.id
            AND business_members.user_id = auth.uid()
        )
    );

-- STORES: Access through business membership
CREATE POLICY "stores_select_through_membership" ON stores
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM business_members
            WHERE business_members.business_id = stores.business_id
            AND business_members.user_id = auth.uid()
        )
    );

-- DOMAINS: Access through store -> business membership
CREATE POLICY "domains_select_through_membership" ON domains
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM stores
            JOIN business_members ON business_members.business_id = stores.business_id
            WHERE domains.store_id = stores.id
            AND business_members.user_id = auth.uid()
        )
    );

-- CATALOGS: Access through store -> business membership
CREATE POLICY "catalogs_select_through_membership" ON catalogs
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM stores
            JOIN business_members ON business_members.business_id = stores.business_id
            WHERE catalogs.store_id = stores.id
            AND business_members.user_id = auth.uid()
        )
    );

-- PRODUCTS: Access through catalog -> store -> business membership
CREATE POLICY "products_select_through_membership" ON products
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM catalogs
            JOIN stores ON stores.id = catalogs.store_id
            JOIN business_members ON business_members.business_id = stores.business_id
            WHERE products.catalog_id = catalogs.id
            AND business_members.user_id = auth.uid()
        )
    );

-- PRODUCT_VARIANTS: Access through product -> catalog -> store -> business
CREATE POLICY "product_variants_select_through_membership" ON product_variants
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM products
            JOIN catalogs ON catalogs.id = products.catalog_id
            JOIN stores ON stores.id = catalogs.store_id
            JOIN business_members ON business_members.business_id = stores.business_id
            WHERE product_variants.product_id = products.id
            AND business_members.user_id = auth.uid()
        )
    );

-- INVENTORY: Access through variant -> product -> catalog -> store -> business
CREATE POLICY "inventory_select_through_membership" ON inventory
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM product_variants
            JOIN products ON products.id = product_variants.product_id
            JOIN catalogs ON catalogs.id = products.catalog_id
            JOIN stores ON stores.id = catalogs.store_id
            JOIN business_members ON business_members.business_id = stores.business_id
            WHERE inventory.product_variant_id = product_variants.id
            AND business_members.user_id = auth.uid()
        )
    );

-- BUSINESS_CONNECTORS: Access through business membership
CREATE POLICY "business_connectors_select_through_membership" ON business_connectors
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM business_members
            WHERE business_members.business_id = business_connectors.business_id
            AND business_members.user_id = auth.uid()
        )
    );

CREATE POLICY "business_connectors_update_as_admin" ON business_connectors
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM business_members
            WHERE business_members.business_id = business_connectors.business_id
            AND business_members.user_id = auth.uid()
            AND business_members.role IN ('owner', 'admin')
        )
    );

-- CONNECTOR_CREDENTIALS: Access through business_connectors
CREATE POLICY "connector_credentials_select_through_membership" ON connector_credentials
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM business_connectors
            JOIN business_members ON business_members.business_id = business_connectors.business_id
            WHERE connector_credentials.business_connector_id = business_connectors.id
            AND business_members.user_id = auth.uid()
            AND business_members.role IN ('owner', 'admin')
        )
    );

-- BUSINESS_CONNECTOR_PERMISSIONS: Access through business_connectors
CREATE POLICY "business_connector_permissions_select_through_membership" ON business_connector_permissions
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM business_connectors
            JOIN business_members ON business_members.business_id = business_connectors.business_id
            WHERE business_connector_permissions.business_connector_id = business_connectors.id
            AND business_members.user_id = auth.uid()
        )
    );

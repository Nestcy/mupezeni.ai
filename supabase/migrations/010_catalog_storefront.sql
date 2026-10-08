-- ============================================================================
-- Migration 010: Catalog & Storefront reconciliations
--
-- Reconciles:
-- 1. products.price -> base_price in integer minor units (e.g. cents/ngwee)
-- 2. Unique store slug and unique product slug per catalog
-- 3. Document images JSON shape
-- ============================================================================

-- 1. Products: ensure base_price column exists and backfill from price
ALTER TABLE products
    ADD COLUMN IF NOT EXISTS base_price INT;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'products' AND column_name = 'price'
    ) THEN
        UPDATE products
        SET base_price = ROUND(price * 100)
        WHERE base_price IS NULL AND price IS NOT NULL;
    END IF;
END
$$;

-- 2. Stores: slug support for public storefronts
ALTER TABLE stores
    ADD COLUMN IF NOT EXISTS slug TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS uq_stores_slug
    ON stores (slug)
    WHERE slug IS NOT NULL;

-- 3. Products: slug support per catalog
ALTER TABLE products
    ADD COLUMN IF NOT EXISTS slug TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS uq_products_catalog_slug
    ON products (catalog_id, slug)
    WHERE slug IS NOT NULL;

-- 4. Images shape documentation comment:
-- Each product.images item is:
-- [{"url": "https://...", "alt": "Description", "position": 0, "is_primary": true}]
COMMENT ON COLUMN products.images IS 'Array of image objects: [{"url": text, "alt": text, "position": int, "is_primary": boolean}]';

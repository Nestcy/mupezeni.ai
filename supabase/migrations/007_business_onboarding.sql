-- ============================================================================
-- Migration 007: business onboarding + channel/catalog connector auth
--
-- Two onboarding paths:
--   existing_retail   business already has a store/catalog elsewhere (Shopify,
--                     WooCommerce, ...) and connects it plus web/WhatsApp/social.
--   mupezeni_managed  no retail store; Mupezeni builds the catalog (web app),
--                     which is then attached as the native "mupezeni" catalog
--                     connector, plus the same channel connectors.
--
-- Writes go through the backend (service role). Safe to re-run.
-- ============================================================================

-- 1. Onboarding state on businesses ------------------------------------------
ALTER TABLE businesses
    ADD COLUMN IF NOT EXISTS onboarding_path   VARCHAR(30),
    ADD COLUMN IF NOT EXISTS onboarding_status VARCHAR(30) NOT NULL DEFAULT 'draft',
    ADD COLUMN IF NOT EXISTS created_by        UUID REFERENCES auth.users(id) ON DELETE SET NULL;

ALTER TABLE businesses DROP CONSTRAINT IF EXISTS businesses_onboarding_path_chk;
ALTER TABLE businesses ADD CONSTRAINT businesses_onboarding_path_chk
    CHECK (onboarding_path IS NULL OR onboarding_path IN ('existing_retail', 'mupezeni_managed'));

ALTER TABLE businesses DROP CONSTRAINT IF EXISTS businesses_onboarding_status_chk;
ALTER TABLE businesses ADD CONSTRAINT businesses_onboarding_status_chk
    CHECK (onboarding_status IN ('draft', 'catalog_pending', 'channels_pending', 'ready', 'active'));

-- 2. Connector routing + encrypted credentials --------------------------------
ALTER TABLE business_connectors
    ADD COLUMN IF NOT EXISTS external_account_id TEXT,   -- WhatsApp phone_number_id, FB page id, IG account id, web site key
    ADD COLUMN IF NOT EXISTS scopes              TEXT[] NOT NULL DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS last_error          TEXT,
    ADD COLUMN IF NOT EXISTS connected_by        UUID REFERENCES auth.users(id) ON DELETE SET NULL;

-- One business owns an external account per provider. Without this, a second
-- tenant could "claim" a number/page and receive another business's inbound
-- messages. Partial: only enforced while the connector is live.
CREATE UNIQUE INDEX IF NOT EXISTS uq_business_connectors_external_account
    ON business_connectors (connector_definition_id, external_account_id)
    WHERE external_account_id IS NOT NULL AND status IN ('connecting', 'connected');

ALTER TABLE connector_credentials
    ADD COLUMN IF NOT EXISTS secret_ciphertext TEXT,      -- Fernet token; plaintext never stored
    ADD COLUMN IF NOT EXISTS key_version      INT NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS rotated_at       TIMESTAMP WITH TIME ZONE;

-- Credentials are never readable by clients, not even owners. Backend only.
DROP POLICY IF EXISTS "connector_credentials_select_through_membership" ON connector_credentials;
REVOKE ALL ON connector_credentials FROM anon, authenticated;

-- 3. Single-use OAuth state ----------------------------------------------------
CREATE TABLE IF NOT EXISTS connector_oauth_states (
    nonce       TEXT PRIMARY KEY,
    business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    user_id     UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    provider    VARCHAR(100) NOT NULL,
    expires_at  TIMESTAMP WITH TIME ZONE NOT NULL,
    used_at     TIMESTAMP WITH TIME ZONE,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
ALTER TABLE connector_oauth_states ENABLE ROW LEVEL SECURITY;   -- no policies: service role only

-- 4. Atomic "create business + owner membership" -------------------------------
CREATE OR REPLACE FUNCTION create_business_with_owner(
    p_user_id uuid, p_name text, p_path text, p_country text, p_currency text,
    p_phone text DEFAULT NULL, p_email text DEFAULT NULL
) RETURNS uuid
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE v_id uuid;
BEGIN
    INSERT INTO businesses (name, onboarding_path, onboarding_status, country, currency, phone, email, created_by)
    VALUES (p_name, p_path, 'catalog_pending', p_country, p_currency, p_phone, p_email, p_user_id)
    RETURNING id INTO v_id;

    INSERT INTO business_members (business_id, user_id, role) VALUES (v_id, p_user_id, 'owner');
    RETURN v_id;
END $$;

REVOKE ALL ON FUNCTION create_business_with_owner(uuid, text, text, text, text, text, text) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION create_business_with_owner(uuid, text, text, text, text, text, text) TO service_role;

-- 5. Supported providers -------------------------------------------------------
INSERT INTO connector_definitions (capability, provider, display_name, status) VALUES
    ('catalog',   'mupezeni',    'Mupezeni Catalog',     'available'),
    ('catalog',   'shopify',     'Shopify',              'available'),
    ('catalog',   'woocommerce', 'WooCommerce',          'available'),
    ('messaging', 'web',         'Website chat widget',  'available'),
    ('messaging', 'whatsapp',    'WhatsApp Business',    'available'),
    ('messaging', 'facebook',    'Facebook Messenger',   'available'),
    ('messaging', 'instagram',   'Instagram DMs',        'available')
ON CONFLICT (capability, provider) DO NOTHING;

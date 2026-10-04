-- ============================================================================
-- Migration 005: CRM, conversations, channels, customer memory + RAG,
--                marketing, business events
--
-- Persists what the Python modules currently keep in in-memory dicts:
--   crm/*            -> customer_identities, customer_interactions, customer_events
--   conversations/*  -> conversations, conversation_state, messages, message_attachments
--   communications/* -> channel_accounts, inbound_webhook_events
--   marketing/*      -> marketing_strategy_profiles, marketing_campaigns,
--                       marketing_content, marketing_approvals, marketing_assets
--   analytics/*      -> business_events
-- Plus (new, not yet in code): customer_memories (per-customer long-term memory)
--   and knowledge_documents / knowledge_chunks (RAG over policies, hours, brand).
--
-- Requires 004 (helper functions). Embedding size is 1536 (OpenAI
-- text-embedding-3-small); change in all three places if you use another model.
-- Safe to re-run.
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions;

-- ============================================================================
-- 1. CHANNEL ACCOUNTS (merchant accounts as data; used to route inbound webhooks)
-- ============================================================================
CREATE TABLE IF NOT EXISTS channel_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    business_connector_id UUID REFERENCES business_connectors(id) ON DELETE SET NULL,
    channel VARCHAR(50) NOT NULL,                 -- web, whatsapp, instagram, facebook, tiktok
    provider VARCHAR(100) NOT NULL,               -- web, meta, tiktok
    external_account_id VARCHAR(255) NOT NULL,    -- WhatsApp phone_number_id, IG/page id, widget key
    display_name VARCHAR(255),
    status VARCHAR(30) NOT NULL DEFAULT 'active', -- active, paused, disconnected
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,  -- never put secrets here; use connector_credentials
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_channel_accounts_provider_ext UNIQUE (provider, external_account_id)
);
CREATE INDEX IF NOT EXISTS idx_channel_accounts_biz ON channel_accounts(business_id);

-- ============================================================================
-- 2. CRM
-- ============================================================================
CREATE TABLE IF NOT EXISTS customer_identities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    channel VARCHAR(50) NOT NULL,                 -- whatsapp, instagram, facebook, web, email, phone
    identity_value VARCHAR(255) NOT NULL,         -- wa number, IG scoped id, web session id, ...
    verified BOOLEAN NOT NULL DEFAULT FALSE,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_customer_identity UNIQUE (business_id, channel, identity_value)
);
CREATE INDEX IF NOT EXISTS idx_customer_identities_customer ON customer_identities(customer_id);

CREATE TABLE IF NOT EXISTS customer_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    event_type VARCHAR(100) NOT NULL,
    source VARCHAR(50) NOT NULL DEFAULT 'system',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_customer_events_customer ON customer_events(customer_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_customer_events_biz ON customer_events(business_id);

-- ============================================================================
-- 3. CONVERSATIONS
-- ============================================================================
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    channel_account_id UUID REFERENCES channel_accounts(id) ON DELETE SET NULL,
    channel VARCHAR(50) NOT NULL DEFAULT 'web',
    channel_conversation_id VARCHAR(255),
    status VARCHAR(30) NOT NULL DEFAULT 'active',          -- active, waiting, closed, archived
    assigned_worker VARCHAR(100),
    current_goal TEXT,
    current_state VARCHAR(40) NOT NULL DEFAULT 'browsing',
    summary TEXT,                                           -- rolling summary for long conversations
    handoff_reason TEXT,
    handed_off_at TIMESTAMPTZ,
    last_message_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_conversations_biz_customer ON conversations(business_id, customer_id);
CREATE INDEX IF NOT EXISTS idx_conversations_biz_status ON conversations(business_id, status, last_message_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS uq_conversations_channel_ref
    ON conversations(business_id, channel, channel_conversation_id) WHERE channel_conversation_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS conversation_state (
    conversation_id UUID PRIMARY KEY REFERENCES conversations(id) ON DELETE CASCADE,
    business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    current_goal TEXT,
    current_product_id UUID REFERENCES products(id) ON DELETE SET NULL,
    current_variant_id UUID REFERENCES product_variants(id) ON DELETE SET NULL,
    cart_id UUID REFERENCES carts(id) ON DELETE SET NULL,
    last_tool VARCHAR(150),
    last_action VARCHAR(150),
    state VARCHAR(40) NOT NULL DEFAULT 'browsing',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_conversation_state_biz ON conversation_state(business_id);

CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    channel VARCHAR(50) NOT NULL DEFAULT 'web',
    sender_type VARCHAR(30) NOT NULL DEFAULT 'customer',    -- customer, worker, owner, system
    sender_id TEXT,
    direction VARCHAR(10) NOT NULL DEFAULT 'inbound',
    message_type VARCHAR(30) NOT NULL DEFAULT 'text',
    content TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    external_message_id VARCHAR(255),
    status VARCHAR(30) NOT NULL DEFAULT 'received',         -- received, processing, processed, failed, ignored, queued, sent, delivered, read
    retry_count INT NOT NULL DEFAULT 0,
    error_code VARCHAR(100),
    last_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_messages_direction CHECK (direction IN ('inbound', 'outbound'))
);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id, created_at);
CREATE INDEX IF NOT EXISTS idx_messages_biz_created ON messages(business_id, created_at DESC);
-- the same provider message is only ever stored once (duplicate webhook deliveries)
CREATE UNIQUE INDEX IF NOT EXISTS uq_messages_external
    ON messages(business_id, channel, external_message_id) WHERE external_message_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS message_attachments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    type VARCHAR(30) NOT NULL,
    url TEXT,
    storage_path TEXT,
    mime_type VARCHAR(100),
    filename VARCHAR(255),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_message_attachments_message ON message_attachments(message_id);

CREATE TABLE IF NOT EXISTS customer_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
    interaction_type VARCHAR(50) NOT NULL,        -- message, order_placed, cart_abandoned, handoff, ...
    channel VARCHAR(50),
    summary TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_customer_interactions_customer ON customer_interactions(customer_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_customer_interactions_biz ON customer_interactions(business_id);

-- Carts, checkouts and orders remember which conversation produced them
ALTER TABLE carts             ADD COLUMN IF NOT EXISTS conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL;
ALTER TABLE checkout_sessions ADD COLUMN IF NOT EXISTS conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL;
ALTER TABLE orders            ADD COLUMN IF NOT EXISTS conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_carts_conversation ON carts(conversation_id);
CREATE INDEX IF NOT EXISTS idx_orders_conversation ON orders(conversation_id);

-- Inbound webhook log + idempotency (WhatsApp / Meta / TikTok / Shopify ...)
CREATE TABLE IF NOT EXISTS inbound_webhook_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID REFERENCES businesses(id) ON DELETE SET NULL,   -- null until routed
    channel_account_id UUID REFERENCES channel_accounts(id) ON DELETE SET NULL,
    provider VARCHAR(50) NOT NULL,
    external_event_id VARCHAR(255) NOT NULL,      -- use a payload hash if the provider sends no id
    event_type VARCHAR(100),
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR(30) NOT NULL DEFAULT 'received',  -- received, processed, failed, ignored
    error TEXT,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMPTZ,
    CONSTRAINT uq_inbound_webhook_provider_evt UNIQUE (provider, external_event_id)
);
CREATE INDEX IF NOT EXISTS idx_inbound_webhook_biz ON inbound_webhook_events(business_id, received_at DESC);
CREATE INDEX IF NOT EXISTS idx_inbound_webhook_status ON inbound_webhook_events(status);

-- ============================================================================
-- 4. CUSTOMER MEMORY (long-term, semantic) AND KNOWLEDGE BASE (RAG)
-- ============================================================================
CREATE TABLE IF NOT EXISTS customer_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
    source_message_id UUID REFERENCES messages(id) ON DELETE SET NULL,
    kind VARCHAR(30) NOT NULL DEFAULT 'fact',     -- preference, fact, summary, objection
    content TEXT NOT NULL,
    importance SMALLINT NOT NULL DEFAULT 3 CHECK (importance BETWEEN 1 AND 5),
    embedding extensions.vector(1536),
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_customer_memories_customer ON customer_memories(business_id, customer_id);
CREATE INDEX IF NOT EXISTS idx_customer_memories_embedding
    ON customer_memories USING hnsw (embedding extensions.vector_cosine_ops);

CREATE TABLE IF NOT EXISTS knowledge_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    kind VARCHAR(30) NOT NULL DEFAULT 'other',    -- policy, faq, hours, brand, about, shipping, returns, other
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'active', -- draft, active, archived
    version INT NOT NULL DEFAULT 1,
    source VARCHAR(30) NOT NULL DEFAULT 'owner',  -- owner, assistant, import
    created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_knowledge_documents_biz ON knowledge_documents(business_id, kind, status);

CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES knowledge_documents(id) ON DELETE CASCADE,
    business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    content TEXT NOT NULL,
    embedding extensions.vector(1536),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_knowledge_chunk UNIQUE (document_id, chunk_index)
);
CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_biz ON knowledge_chunks(business_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_embedding
    ON knowledge_chunks USING hnsw (embedding extensions.vector_cosine_ops);

-- Tenant-scoped similarity search. Always pass the business_id.
CREATE OR REPLACE FUNCTION match_knowledge_chunks(
    p_business_id uuid, p_query_embedding extensions.vector,
    p_match_count int DEFAULT 5, p_min_similarity float DEFAULT 0.0
) RETURNS TABLE (chunk_id uuid, document_id uuid, content text, similarity float, metadata jsonb)
LANGUAGE sql STABLE SET search_path = public, extensions AS $$
    SELECT k.id, k.document_id, k.content,
           (1 - (k.embedding <=> p_query_embedding))::float AS similarity, k.metadata
      FROM knowledge_chunks k
      JOIN knowledge_documents d ON d.id = k.document_id AND d.status = 'active'
     WHERE k.business_id = p_business_id
       AND k.embedding IS NOT NULL
       AND (1 - (k.embedding <=> p_query_embedding)) >= p_min_similarity
     ORDER BY k.embedding <=> p_query_embedding
     LIMIT p_match_count;
$$;

CREATE OR REPLACE FUNCTION match_customer_memories(
    p_business_id uuid, p_customer_id uuid, p_query_embedding extensions.vector,
    p_match_count int DEFAULT 5, p_min_similarity float DEFAULT 0.0
) RETURNS TABLE (memory_id uuid, kind text, content text, importance smallint, similarity float)
LANGUAGE sql STABLE SET search_path = public, extensions AS $$
    SELECT m.id, m.kind::text, m.content, m.importance,
           (1 - (m.embedding <=> p_query_embedding))::float AS similarity
      FROM customer_memories m
     WHERE m.business_id = p_business_id
       AND m.customer_id = p_customer_id
       AND m.embedding IS NOT NULL
       AND (m.expires_at IS NULL OR m.expires_at > NOW())
       AND (1 - (m.embedding <=> p_query_embedding)) >= p_min_similarity
     ORDER BY m.embedding <=> p_query_embedding
     LIMIT p_match_count;
$$;

-- ============================================================================
-- 5. MARKETING
-- (budget columns are NUMERIC to match the Python models; they are plans, not a ledger)
-- ============================================================================
CREATE TABLE IF NOT EXISTS marketing_strategy_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL UNIQUE REFERENCES businesses(id) ON DELETE CASCADE,
    business_goal TEXT NOT NULL,
    primary_products JSONB NOT NULL DEFAULT '[]'::jsonb,
    target_customers TEXT,
    monthly_ad_budget NUMERIC(14, 2),
    currency VARCHAR(3) NOT NULL DEFAULT 'ZMW',
    preferred_platforms JSONB NOT NULL DEFAULT '[]'::jsonb,
    brand_positioning JSONB NOT NULL DEFAULT '[]'::jsonb,
    discount_policy JSONB NOT NULL DEFAULT '{}'::jsonb,
    approval_policy JSONB NOT NULL DEFAULT '{}'::jsonb,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS marketing_campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    objective VARCHAR(30) NOT NULL,               -- sales, product_launch, awareness, engagement, traffic, retention
    status VARCHAR(30) NOT NULL DEFAULT 'draft',  -- draft, planning, pending_approval, approved, active, paused, completed, cancelled
    target_audience TEXT,
    budget NUMERIC(14, 2),
    currency VARCHAR(3) NOT NULL DEFAULT 'ZMW',
    start_at TIMESTAMPTZ,
    end_at TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_marketing_campaigns_biz ON marketing_campaigns(business_id, status);

CREATE TABLE IF NOT EXISTS marketing_approvals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    request_type VARCHAR(50) NOT NULL,            -- publish_post, launch_campaign, ...
    resource_type VARCHAR(30) NOT NULL,           -- content, campaign, asset
    resource_id TEXT NOT NULL,
    requested_by TEXT NOT NULL,                   -- worker id or user id
    status VARCHAR(30) NOT NULL DEFAULT 'pending',-- pending, approved, rejected, expired, cancelled
    risk VARCHAR(10) NOT NULL DEFAULT 'low',      -- low, medium, high
    is_paid BOOLEAN NOT NULL DEFAULT FALSE,       -- paid spend vs organic
    estimated_spend NUMERIC(14, 2),
    reason TEXT,
    requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reviewed_at TIMESTAMPTZ,
    reviewed_by TEXT,
    review_comment TEXT,
    expires_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_marketing_approvals_biz_status ON marketing_approvals(business_id, status);

CREATE TABLE IF NOT EXISTS marketing_content (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    created_by_worker BOOLEAN NOT NULL DEFAULT TRUE,
    content_type VARCHAR(30) NOT NULL,            -- social_post, caption, ad_copy, ad_concept, ...
    status VARCHAR(30) NOT NULL DEFAULT 'draft',  -- draft, pending_approval, approved, rejected, published, archived
    title VARCHAR(255),
    body TEXT NOT NULL,
    caption TEXT,
    platform VARCHAR(50),
    product_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    campaign_id UUID REFERENCES marketing_campaigns(id) ON DELETE SET NULL,
    brand_context_version VARCHAR(50),
    approval_id UUID REFERENCES marketing_approvals(id) ON DELETE SET NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_marketing_content_biz ON marketing_content(business_id, status);
CREATE INDEX IF NOT EXISTS idx_marketing_content_campaign ON marketing_content(campaign_id);

-- Generated images, with the generate -> review -> refine chain (V1: images only)
CREATE TABLE IF NOT EXISTS marketing_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    content_id UUID REFERENCES marketing_content(id) ON DELETE SET NULL,
    parent_asset_id UUID REFERENCES marketing_assets(id) ON DELETE SET NULL,
    asset_type VARCHAR(20) NOT NULL DEFAULT 'image',
    storage_path TEXT NOT NULL,                   -- Supabase Storage path
    public_url TEXT,
    prompt TEXT,
    model VARCHAR(100),
    iteration INT NOT NULL DEFAULT 1,
    status VARCHAR(20) NOT NULL DEFAULT 'draft',  -- draft, approved, rejected
    review_notes TEXT,                            -- the reflection-loop critique
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_marketing_assets_biz ON marketing_assets(business_id);
CREATE INDEX IF NOT EXISTS idx_marketing_assets_content ON marketing_assets(content_id);

-- ============================================================================
-- 6. BUSINESS EVENTS (Seeker / analytics signal log; rows cannot be updated)
-- ============================================================================
CREATE TABLE IF NOT EXISTS business_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    event_type VARCHAR(100) NOT NULL,             -- e.g. checkout.created, payment.paid, cart.abandoned
    source VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id TEXT NOT NULL,
    idempotency_key TEXT,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_business_events_type ON business_events(business_id, event_type, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_business_events_entity ON business_events(business_id, entity_type, entity_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_business_events_idempotency
    ON business_events(business_id, idempotency_key) WHERE idempotency_key IS NOT NULL;

CREATE OR REPLACE FUNCTION prevent_row_update() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION '% is append-only; rows cannot be updated', TG_TABLE_NAME;
END $$;

DROP TRIGGER IF EXISTS trg_business_events_no_update ON business_events;
CREATE TRIGGER trg_business_events_no_update BEFORE UPDATE ON business_events
    FOR EACH ROW EXECUTE FUNCTION prevent_row_update();

-- ============================================================================
-- 7. RLS (members can read their business's rows; writes go through the backend)
-- ============================================================================
SELECT apply_member_select_policy(t) FROM unnest(ARRAY[
    'channel_accounts', 'customer_identities', 'customer_events', 'customer_interactions',
    'conversations', 'conversation_state', 'messages', 'message_attachments',
    'inbound_webhook_events', 'customer_memories', 'knowledge_documents', 'knowledge_chunks',
    'marketing_strategy_profiles', 'marketing_campaigns', 'marketing_approvals',
    'marketing_content', 'marketing_assets', 'business_events'
]) AS t;

-- ============================================================================
-- 8. updated_at triggers for the new tables
-- ============================================================================
SELECT apply_updated_at_triggers();

-- ============================================================================
-- Migration 008: Foundation — jobs queue, agent runs, AI settings, web sessions
--
-- Apply with:  supabase db push  (or paste into Supabase SQL editor)
-- Safe to re-run: all DDL uses IF NOT EXISTS / IF NOT EXISTS guards.
-- ============================================================================

-- ── 1. agent_runs ────────────────────────────────────────────────────────────
-- One row per AI agent invocation.  Linked to conversation + triggering message.
-- cost_usd is filled by the worker after the run completes.

CREATE TABLE IF NOT EXISTS agent_runs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id         UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    worker_id           TEXT NOT NULL,                          -- e.g. "customer_revenue"
    conversation_id     UUID REFERENCES conversations(id) ON DELETE SET NULL,
    trigger_message_id  UUID,                                   -- messages.id that started this run
    trace_id            TEXT NOT NULL,                          -- single trace threaded through entire flow
    status              TEXT NOT NULL DEFAULT 'running'
                            CHECK (status IN ('running','succeeded','failed','timed_out')),
    model               TEXT,                                   -- actual model used (may differ from config)
    fallback_used       BOOLEAN NOT NULL DEFAULT FALSE,
    iterations          INT NOT NULL DEFAULT 0,
    tool_calls          INT NOT NULL DEFAULT 0,
    prompt_tokens       INT NOT NULL DEFAULT 0,
    completion_tokens   INT NOT NULL DEFAULT 0,
    cost_usd            NUMERIC(10,6) NOT NULL DEFAULT 0,
    error               TEXT,
    started_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at         TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_agent_runs_business_conversation
    ON agent_runs (business_id, conversation_id, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_agent_runs_trace
    ON agent_runs (trace_id);

-- ── 2. capability_executions — add run_id + trace_id ─────────────────────────
-- Guard: only add if the table already exists (created in migration 004).
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'capability_executions') THEN
        ALTER TABLE capability_executions
            ADD COLUMN IF NOT EXISTS run_id   UUID REFERENCES agent_runs(id) ON DELETE SET NULL,
            ADD COLUMN IF NOT EXISTS trace_id TEXT;
    END IF;
END
$$;

-- ── 3. jobs — durable queue ──────────────────────────────────────────────────
-- The Supabase PostgREST client cannot express FOR UPDATE SKIP LOCKED, so
-- claim/complete/fail are SQL functions (see below) called via supabase.rpc().

CREATE TABLE IF NOT EXISTS jobs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id     UUID REFERENCES businesses(id) ON DELETE CASCADE,
    type            TEXT NOT NULL,                              -- e.g. "customer.reply", "channel.send"
    payload         JSONB NOT NULL DEFAULT '{}',
    run_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),         -- earliest execution time
    status          TEXT NOT NULL DEFAULT 'queued'
                        CHECK (status IN ('queued','running','succeeded','failed','dead','cancelled')),
    attempts        INT NOT NULL DEFAULT 0,
    max_attempts    INT NOT NULL DEFAULT 3,
    locked_by       TEXT,                                       -- worker_id holding the lock
    locked_at       TIMESTAMPTZ,
    last_error      TEXT,
    idempotency_key TEXT UNIQUE,                                -- prevents duplicate enqueuing
    trace_id        TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Partial index on claimable rows only (keeps it small; succeeded/dead rows excluded)
CREATE INDEX IF NOT EXISTS idx_jobs_claim
    ON jobs (run_at, type)
    WHERE status IN ('queued', 'failed');

CREATE INDEX IF NOT EXISTS idx_jobs_business_status
    ON jobs (business_id, status, created_at DESC);

-- ── SQL functions (SKIP LOCKED cannot be expressed by the Supabase client) ───

-- claim_jobs: atomically claim up to p_limit jobs of the given types.
-- Called by the worker via supabase.rpc("claim_jobs", {...}).
CREATE OR REPLACE FUNCTION claim_jobs(
    p_worker    TEXT,
    p_limit     INT,
    p_types     TEXT[]   -- NULL means any type
)
RETURNS SETOF jobs
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
        UPDATE jobs
        SET
            status    = 'running',
            locked_by = p_worker,
            locked_at = NOW(),
            attempts  = attempts + 1
        WHERE id IN (
            SELECT id
            FROM   jobs
            WHERE  status IN ('queued', 'failed')
              AND  run_at <= NOW()
              AND  (p_types IS NULL OR type = ANY(p_types))
              AND  attempts < max_attempts
            ORDER BY run_at
            LIMIT  p_limit
            FOR UPDATE SKIP LOCKED
        )
        RETURNING *;
END;
$$;

-- complete_job: mark a job succeeded and release the lock.
CREATE OR REPLACE FUNCTION complete_job(p_id UUID)
RETURNS VOID
LANGUAGE sql
AS $$
    UPDATE jobs
    SET    status    = 'succeeded',
           locked_by = NULL,
           locked_at = NULL
    WHERE  id = p_id;
$$;

-- fail_job: increment attempts; apply exponential backoff or dead-letter.
-- Backoff: run_at = NOW() + 2^attempts seconds (1s, 2s, 4s, 8s …).
CREATE OR REPLACE FUNCTION fail_job(p_id UUID, p_error TEXT)
RETURNS VOID
LANGUAGE plpgsql
AS $$
DECLARE
    v_attempts     INT;
    v_max_attempts INT;
BEGIN
    SELECT attempts, max_attempts
    INTO   v_attempts, v_max_attempts
    FROM   jobs
    WHERE  id = p_id;

    IF v_attempts >= v_max_attempts THEN
        UPDATE jobs
        SET    status     = 'dead',
               last_error = p_error,
               locked_by  = NULL,
               locked_at  = NULL
        WHERE  id = p_id;
    ELSE
        UPDATE jobs
        SET    status     = 'failed',
               last_error = p_error,
               locked_by  = NULL,
               locked_at  = NULL,
               -- exponential backoff: 2^attempts seconds, capped at 1 hour
               run_at     = NOW() + LEAST(
                                POWER(2, v_attempts) * INTERVAL '1 second',
                                INTERVAL '1 hour'
                            )
        WHERE  id = p_id;
    END IF;
END;
$$;

-- ── 4. conversations — add Phase 0 columns ───────────────────────────────────

ALTER TABLE conversations
    ADD COLUMN IF NOT EXISTS last_customer_message_at  TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS ai_enabled                BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS ai_paused_by              UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS unread_count              INT NOT NULL DEFAULT 0;

-- Trigger: maintain last_customer_message_at + unread_count on inbound messages.
-- We only update on DIRECTION='inbound' (customer → us).
-- The trigger checks for a "direction" column; if it doesn't exist we fall back
-- to updating on every insert (safe, just slightly over-counts).
CREATE OR REPLACE FUNCTION trg_conversations_on_message()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    -- Only update on inbound customer messages
    IF (TG_OP = 'INSERT') AND (
        NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE  table_name = 'messages' AND column_name = 'direction'
        )
        OR NEW.direction = 'inbound'
    ) THEN
        UPDATE conversations
        SET    last_customer_message_at = COALESCE(NEW.created_at, NOW()),
               unread_count             = unread_count + 1
        WHERE  id = NEW.conversation_id;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_messages_update_conversation ON messages;
CREATE TRIGGER trg_messages_update_conversation
    AFTER INSERT ON messages
    FOR EACH ROW EXECUTE FUNCTION trg_conversations_on_message();

-- ── 5. message_templates ─────────────────────────────────────────────────────
-- WhatsApp / Meta approved templates.  Pending approval until Meta confirms.

CREATE TABLE IF NOT EXISTS message_templates (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id             UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    connector_id            UUID REFERENCES business_connectors(id) ON DELETE SET NULL,
    name                    TEXT NOT NULL,
    language                TEXT NOT NULL DEFAULT 'en',
    category                TEXT NOT NULL,              -- e.g. "MARKETING", "UTILITY"
    body                    TEXT NOT NULL,
    variables               JSONB NOT NULL DEFAULT '[]',
    status                  TEXT NOT NULL DEFAULT 'pending'
                                CHECK (status IN ('pending','approved','rejected')),
    external_template_id    TEXT,                       -- Meta's template id once approved
    rejection_reason        TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_message_templates_name_language
    ON message_templates (business_id, name, language);

-- ── 6. web_sessions — visitor token for the web widget ───────────────────────
-- A visitor POSTs to /channels/web/{site_key}/session → gets a short-lived token.
-- The token_hash (SHA-256 of the raw token) is stored; the raw token is never persisted.

CREATE TABLE IF NOT EXISTS web_sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id     UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    site_key        TEXT NOT NULL,
    token_hash      TEXT NOT NULL UNIQUE,               -- SHA-256(raw_token), hex
    customer_id     UUID REFERENCES customers(id) ON DELETE SET NULL,
    conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
    expires_at      TIMESTAMPTZ NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_web_sessions_site_key
    ON web_sessions (business_id, site_key);

-- ── 7. business_ai_settings ──────────────────────────────────────────────────
-- Per-business AI configuration.  Created with safe defaults on first-use.

CREATE TABLE IF NOT EXISTS business_ai_settings (
    business_id             UUID PRIMARY KEY REFERENCES businesses(id) ON DELETE CASCADE,
    ai_enabled              BOOLEAN NOT NULL DEFAULT TRUE,
    autonomy_level          TEXT NOT NULL DEFAULT 'auto'
                                CHECK (autonomy_level IN ('auto','suggest','off')),
    timezone                TEXT NOT NULL DEFAULT 'Africa/Lusaka',
    business_hours          JSONB NOT NULL DEFAULT '{}',
                            -- Example: {"mon":{"open":"08:00","close":"17:00"}, ...}
    handoff_keywords        TEXT[] NOT NULL DEFAULT '{}',
                            -- Customer phrases that trigger human handoff
    daily_llm_budget_usd    NUMERIC(8,2) NOT NULL DEFAULT 5.00,
    monthly_llm_budget_usd  NUMERIC(10,2) NOT NULL DEFAULT 100.00,
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── 8. Seed connector_capabilities ──────────────────────────────────────────
-- Without these rows, every worker tool call is denied at the permission check.
-- We insert the full set of capability/provider combinations and set low-risk
-- actions to enabled=true, high-risk to requires_approval=true.

-- Guard: only seed if the table exists (created in migration 004).
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables WHERE table_name = 'connector_capabilities'
    ) THEN
        -- catalog provider capabilities
        INSERT INTO connector_capabilities (connector_definition_id, capability, enabled, requires_approval)
        SELECT cd.id, cap.capability, cap.enabled, cap.requires_approval
        FROM   connector_definitions cd
        CROSS JOIN (VALUES
            ('catalog.search_products',     TRUE,  FALSE),
            ('catalog.get_product',         TRUE,  FALSE),
            ('catalog.check_availability',  TRUE,  FALSE),
            ('inventory.get',               TRUE,  FALSE),
            ('inventory.reserve',           TRUE,  FALSE),
            ('inventory.release',           TRUE,  FALSE),
            ('inventory.adjust',            FALSE, TRUE),
            ('cart.create',                 TRUE,  FALSE),
            ('cart.get',                    TRUE,  FALSE),
            ('cart.add_item',               TRUE,  FALSE),
            ('cart.update_item',            TRUE,  FALSE),
            ('cart.remove_item',            TRUE,  FALSE),
            ('order.create',                TRUE,  FALSE),
            ('order.get',                   TRUE,  FALSE),
            ('order.cancel',                FALSE, TRUE)
        ) AS cap(capability, enabled, requires_approval)
        WHERE  cd.provider IN ('mupezeni', 'shopify', 'woocommerce')
        ON CONFLICT DO NOTHING;

        -- messaging provider capabilities
        INSERT INTO connector_capabilities (connector_definition_id, capability, enabled, requires_approval)
        SELECT cd.id, cap.capability, cap.enabled, cap.requires_approval
        FROM   connector_definitions cd
        CROSS JOIN (VALUES
            ('message.send',        TRUE,  FALSE),
            ('message.send_template', TRUE, FALSE)
        ) AS cap(capability, enabled, requires_approval)
        WHERE  cd.provider IN ('whatsapp', 'facebook', 'instagram', 'web')
        ON CONFLICT DO NOTHING;
    END IF;
END
$$;

-- ── 9. Seed trigger: auto-create business_connector_permissions on connect ───
-- When a business connects a new connector, seed permissions from
-- connector_capabilities so the worker can immediately use low-risk actions.
CREATE OR REPLACE FUNCTION trg_seed_connector_permissions()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    -- Only run if business_connector_permissions exists
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE  table_name = 'business_connector_permissions'
    ) THEN
        INSERT INTO business_connector_permissions (
            business_connector_id, capability, enabled, requires_approval
        )
        SELECT
            NEW.id,
            cc.capability,
            cc.enabled,
            cc.requires_approval
        FROM connector_capabilities cc
        WHERE cc.connector_definition_id = NEW.connector_definition_id
        ON CONFLICT DO NOTHING;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_business_connectors_seed_permissions ON business_connectors;
CREATE TRIGGER trg_business_connectors_seed_permissions
    AFTER INSERT ON business_connectors
    FOR EACH ROW EXECUTE FUNCTION trg_seed_connector_permissions();

-- ============================================================================
-- Migration 006: database-side support for the persistence layer
--
--   1. resolve_customer()      atomic "find or create customer for a channel handle"
--   2. enforce_same_business() blocks rows that point at another tenant's parent
--                              (e.g. a message in business A on a conversation of B)
--   3. messages -> conversation/customer bookkeeping (last_message_at, last_seen_at)
--
-- Requires 004 + 005. Safe to re-run.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. Atomic customer resolution (no duplicate customers when two webhooks race)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION resolve_customer(
    p_business_id uuid,
    p_channel text,
    p_identity_value text,
    p_display_name text DEFAULT NULL,
    p_phone text DEFAULT NULL,
    p_email text DEFAULT NULL
) RETURNS TABLE (out_customer_id uuid, out_created boolean)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE
    v_customer uuid;
    v_rows int;
BEGIN
    IF p_business_id IS NULL OR p_channel IS NULL OR p_identity_value IS NULL OR p_identity_value = '' THEN
        RAISE EXCEPTION 'business_id, channel and identity_value are required';
    END IF;

    SELECT i.customer_id INTO v_customer
      FROM customer_identities i
     WHERE i.business_id = p_business_id AND i.channel = p_channel AND i.identity_value = p_identity_value;

    IF v_customer IS NOT NULL THEN
        UPDATE customers SET last_seen_at = NOW() WHERE id = v_customer;
        RETURN QUERY SELECT v_customer, FALSE;
        RETURN;
    END IF;

    INSERT INTO customers (business_id, display_name, phone, email, first_seen_at, last_seen_at)
    VALUES (p_business_id, p_display_name,
            COALESCE(p_phone, CASE WHEN p_channel = 'whatsapp' THEN p_identity_value END),
            p_email, NOW(), NOW())
    RETURNING id INTO v_customer;

    INSERT INTO customer_identities (business_id, customer_id, channel, identity_value, metadata)
    VALUES (p_business_id, v_customer, p_channel, p_identity_value,
            CASE WHEN p_display_name IS NOT NULL THEN jsonb_build_object('display_name', p_display_name) ELSE '{}'::jsonb END)
    ON CONFLICT (business_id, channel, identity_value) DO NOTHING;
    GET DIAGNOSTICS v_rows = ROW_COUNT;

    IF v_rows = 0 THEN
        -- lost the race: discard our customer, return the winner's
        DELETE FROM customers WHERE id = v_customer;
        SELECT i.customer_id INTO v_customer
          FROM customer_identities i
         WHERE i.business_id = p_business_id AND i.channel = p_channel AND i.identity_value = p_identity_value;
        RETURN QUERY SELECT v_customer, FALSE;
        RETURN;
    END IF;

    RETURN QUERY SELECT v_customer, TRUE;
END $$;

REVOKE ALL ON FUNCTION resolve_customer(uuid, text, text, text, text, text) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION resolve_customer(uuid, text, text, text, text, text) TO service_role;

-- ----------------------------------------------------------------------------
-- 2. Cross-tenant guard
--    CREATE TRIGGER ... EXECUTE FUNCTION enforce_same_business('<parent_table>', '<fk_column>')
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION enforce_same_business() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    v_parent_business uuid;
    v_parent_id uuid := (to_jsonb(NEW) ->> TG_ARGV[1])::uuid;
BEGIN
    IF v_parent_id IS NULL THEN
        RETURN NEW;
    END IF;
    EXECUTE format('SELECT business_id FROM public.%I WHERE id = $1', TG_ARGV[0])
       INTO v_parent_business USING v_parent_id;
    IF v_parent_business IS NOT NULL AND v_parent_business IS DISTINCT FROM NEW.business_id THEN
        RAISE EXCEPTION 'cross-tenant reference: %.% points at a % owned by a different business',
            TG_TABLE_NAME, TG_ARGV[1], TG_ARGV[0]
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END $$;

DO $$
DECLARE r record;
BEGIN
    FOR r IN SELECT * FROM (VALUES
        ('messages',              'conversations',        'conversation_id'),
        ('conversation_state',    'conversations',        'conversation_id'),
        ('conversations',         'customers',            'customer_id'),
        ('customer_memories',     'customers',            'customer_id'),
        ('customer_interactions', 'customers',            'customer_id'),
        ('customer_identities',   'customers',            'customer_id'),
        ('customer_events',       'customers',            'customer_id'),
        ('customer_addresses',    'customers',            'customer_id'),
        ('knowledge_chunks',      'knowledge_documents',  'document_id')
    ) AS t(child, parent, fk)
    LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS trg_same_business ON public.%I', r.child);
        EXECUTE format('CREATE TRIGGER trg_same_business BEFORE INSERT OR UPDATE ON public.%I '
                       'FOR EACH ROW EXECUTE FUNCTION enforce_same_business(%L, %L)',
                       r.child, r.parent, r.fk);
    END LOOP;
END $$;

-- ----------------------------------------------------------------------------
-- 3. Message bookkeeping
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION on_message_inserted() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN
    UPDATE conversations
       SET last_message_at = GREATEST(COALESCE(last_message_at, NEW.created_at), NEW.created_at),
           updated_at = NOW()
     WHERE id = NEW.conversation_id;
    IF NEW.direction = 'inbound' THEN
        UPDATE customers SET last_seen_at = NEW.created_at
         WHERE id = (SELECT customer_id FROM conversations WHERE id = NEW.conversation_id);
    END IF;
    RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS trg_messages_bookkeeping ON messages;
CREATE TRIGGER trg_messages_bookkeeping AFTER INSERT ON messages
    FOR EACH ROW EXECUTE FUNCTION on_message_inserted();

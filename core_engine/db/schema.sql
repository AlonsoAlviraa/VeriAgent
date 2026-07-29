-- ============================================
-- VeriAgent DDL - PostgreSQL
-- [TEAM-A][CORE-002] Database Schema
-- ============================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- INVOICES TABLE
-- ============================================
CREATE TABLE invoices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001',
    series VARCHAR(10) NOT NULL,
    number VARCHAR(50) NOT NULL,
    issue_date DATE NOT NULL,
    
    -- Parties
    issuer_tax_id VARCHAR(20) NOT NULL,
    customer_tax_id VARCHAR(20) NOT NULL,
    customer_name VARCHAR(255) NOT NULL,
    
    -- Amounts
    total_base DECIMAL(15,2) NOT NULL,
    total_tax DECIMAL(15,2) NOT NULL,
    total_amount DECIMAL(15,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'EUR',
    
    -- VeriFactu Chaining
    invoice_hash VARCHAR(64) NOT NULL,
    previous_invoice_hash VARCHAR(64),
    
    -- Metadata
    xml_content TEXT,
    signature BYTEA,
    qr_payload TEXT,
    aeat_csv VARCHAR(50),
    -- COMP-03: statuses aligned with API/AEAT audit traffic-light
    status VARCHAR(20) DEFAULT 'PENDING' CHECK (status IN (
        'PENDING', 'VALIDATED', 'SIGNED', 'SENT', 'SENT_OK', 'REJECTED_AEAT', 'ERROR'
    )),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints (tenant-scoped uniqueness)
    CONSTRAINT unique_invoice UNIQUE (tenant_id, series, number, issuer_tax_id),
    CONSTRAINT valid_amounts CHECK (total_amount = total_base + total_tax)
);

-- Indexes for common queries
CREATE INDEX idx_invoices_issuer ON invoices(issuer_tax_id);
CREATE INDEX idx_invoices_tenant ON invoices(tenant_id);
CREATE INDEX idx_invoices_date ON invoices(issue_date);
CREATE INDEX idx_invoices_hash ON invoices(invoice_hash);
CREATE INDEX idx_invoices_status ON invoices(status);

-- Durable chain tips per tenant + issuer (COMP-02 / MT-02)
CREATE TABLE IF NOT EXISTS chain_tips (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL,
    issuer_tax_id VARCHAR(20) NOT NULL,
    tip_hash VARCHAR(64) NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_chain_tip UNIQUE (tenant_id, issuer_tax_id)
);

-- ============================================
-- AUDIT_LOGS TABLE
-- ============================================
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    invoice_id UUID REFERENCES invoices(id),
    
    action VARCHAR(50) NOT NULL,
    actor VARCHAR(100) NOT NULL, -- 'SYSTEM', 'AGENT:fiscal_auditor', 'USER:xxx'
    
    details JSONB,
    
    -- Hash integrity
    previous_log_hash VARCHAR(64),
    log_hash VARCHAR(64) NOT NULL,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_audit_invoice ON audit_logs(invoice_id);
CREATE INDEX idx_audit_action ON audit_logs(action);
CREATE INDEX idx_audit_created ON audit_logs(created_at);

-- ============================================
-- HASH CHAIN INTEGRITY TRIGGER
-- ============================================
CREATE OR REPLACE FUNCTION validate_hash_chain()
RETURNS TRIGGER AS $$
DECLARE
    last_hash VARCHAR(64);
BEGIN
    -- Tenant-scoped tip for this issuer (MT-02)
    SELECT invoice_hash INTO last_hash
    FROM invoices
    WHERE issuer_tax_id = NEW.issuer_tax_id
      AND tenant_id = NEW.tenant_id
      AND id IS DISTINCT FROM NEW.id
    ORDER BY created_at DESC
    LIMIT 1;
    
    -- Validate chain (if not first invoice for tenant+issuer)
    IF last_hash IS NOT NULL AND NEW.previous_invoice_hash IS DISTINCT FROM last_hash THEN
        RAISE EXCEPTION 'Hash chain broken: expected previous_hash=%, got=%', 
            last_hash, NEW.previous_invoice_hash;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_validate_hash_chain
    BEFORE INSERT ON invoices
    FOR EACH ROW
    EXECUTE FUNCTION validate_hash_chain();

-- ============================================
-- CONTROL PLANE (PR-MT-01) — multi-tenant registry
-- Hybrid ADR: control plane + shared/default data plane on same Postgres
-- ============================================

CREATE TABLE IF NOT EXISTS plans (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    slug VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    plan_id VARCHAR(50) NOT NULL REFERENCES plans(id),
    status VARCHAR(20) NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'suspended', 'pending')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tenants_plan ON tenants(plan_id);
CREATE INDEX IF NOT EXISTS idx_tenants_status ON tenants(status);

CREATE TABLE IF NOT EXISTS data_plane_bindings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL UNIQUE REFERENCES tenants(id) ON DELETE CASCADE,
    tier VARCHAR(20) NOT NULL CHECK (tier IN ('standard', 'enterprise')),
    -- Logical ref only (e.g. shared-default | tenant:<uuid>); secrets stay out of this table
    connection_ref VARCHAR(512) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dpb_tier ON data_plane_bindings(tier);

CREATE TABLE IF NOT EXISTS feature_flags (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    flag_key VARCHAR(100) NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_tenant_flag UNIQUE (tenant_id, flag_key)
);

CREATE INDEX IF NOT EXISTS idx_feature_flags_key ON feature_flags(flag_key);

-- ============================================
-- WEBHOOKS (CORE-011) — durable outbox + retry + dead-letter
-- ============================================

CREATE TABLE IF NOT EXISTS webhook_subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    url VARCHAR(1024) NOT NULL,
    -- Eventos a los que se suscribe (vacío = todos). JSON array de strings.
    events JSONB NOT NULL DEFAULT '[]'::jsonb,
    secret VARCHAR(255),  -- para HMAC signing del payload
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_webhook_subs_tenant ON webhook_subscriptions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_webhook_subs_active ON webhook_subscriptions(active);

-- Outbox de entregas pendientes/procesadas (pattern outbox + dead-letter).
CREATE TABLE IF NOT EXISTS webhook_deliveries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    subscription_id UUID NOT NULL REFERENCES webhook_subscriptions(id) ON DELETE CASCADE,
    event VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL,
    -- PENDING | DELIVERED | RETRY | DEAD_LETTER
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING','DELIVERED','RETRY','DEAD_LETTER')),
    attempts INT NOT NULL DEFAULT 0,
    max_attempts INT NOT NULL DEFAULT 5,
    last_error TEXT,
    next_attempt_at TIMESTAMP,
    delivered_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_status ON webhook_deliveries(status);
CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_next ON webhook_deliveries(next_attempt_at)
    WHERE status IN ('PENDING', 'RETRY');

-- ============================================
-- AUTH / SESSIONS (MT-05 / Sprint 7) — persistent 2FA state
-- ============================================

CREATE TABLE IF NOT EXISTS org_memberships (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(100) NOT NULL,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL CHECK (role IN ('issuer','auditor','admin')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, tenant_id)
);

CREATE INDEX IF NOT EXISTS idx_org_memberships_user ON org_memberships(user_id);
CREATE INDEX IF NOT EXISTS idx_org_memberships_tenant ON org_memberships(tenant_id);

CREATE TABLE IF NOT EXISTS user_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(100) NOT NULL,
    active_tenant_id UUID NOT NULL,
    roles_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    twofa_verified_at TIMESTAMP,
    twofa_expires_at TIMESTAMP,
    twofa_method VARCHAR(20) CHECK (twofa_method IN ('totp','trusted_device'))
);

CREATE INDEX IF NOT EXISTS idx_user_sessions_user ON user_sessions(user_id);

-- Seed plans (idempotent)
INSERT INTO plans (id, name, description) VALUES
    ('standard', 'Standard', 'Shared Postgres + RLS multi-tenant tier'),
    ('enterprise', 'Enterprise', 'DB-per-tenant data plane for regulated cohorts')
ON CONFLICT (id) DO NOTHING;

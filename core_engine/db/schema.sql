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
    status VARCHAR(20) DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'VALIDATED', 'SIGNED', 'SENT', 'ERROR')),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT unique_invoice UNIQUE (series, number, issuer_tax_id),
    CONSTRAINT valid_amounts CHECK (total_amount = total_base + total_tax)
);

-- Indexes for common queries
CREATE INDEX idx_invoices_issuer ON invoices(issuer_tax_id);
CREATE INDEX idx_invoices_date ON invoices(issue_date);
CREATE INDEX idx_invoices_hash ON invoices(invoice_hash);
CREATE INDEX idx_invoices_status ON invoices(status);

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
    -- Get the hash of the last invoice for this issuer
    SELECT invoice_hash INTO last_hash
    FROM invoices
    WHERE issuer_tax_id = NEW.issuer_tax_id
    ORDER BY created_at DESC
    LIMIT 1;
    
    -- Validate chain (if not first invoice)
    IF last_hash IS NOT NULL AND NEW.previous_invoice_hash != last_hash THEN
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

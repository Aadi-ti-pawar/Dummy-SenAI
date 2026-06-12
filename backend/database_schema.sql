-- SenAI CRM Intelligence Platform - Database Schema
-- PostgreSQL 17+ with pgvector support for embeddings

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- ============================================================================
-- TRIGGER FUNCTION - Auto-update updated_at timestamp
-- ============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 1. CONTACTS TABLE - CRM Profiles
-- ============================================================================
CREATE TABLE IF NOT EXISTS contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255),
    company VARCHAR(255),
    status VARCHAR(50) DEFAULT 'Active' CHECK (status IN ('Active', 'VIP', 'Blocked', 'Churned')),
    account_value DECIMAL(12, 2) DEFAULT 0.00,
    churn_risk_score DECIMAL(3, 2) DEFAULT 0.00 CHECK (churn_risk_score BETWEEN 0.00 AND 1.00),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_contact_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_contacts_email ON contacts(email);
CREATE INDEX idx_contacts_status ON contacts(status);
CREATE INDEX idx_contacts_churn_risk ON contacts(churn_risk_score DESC);
CREATE INDEX idx_contacts_last_contact ON contacts(last_contact_at DESC);

CREATE TRIGGER update_contacts_updated_at BEFORE UPDATE ON contacts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- 2. THREADS TABLE - Email Conversation Threads
-- ============================================================================
CREATE TABLE IF NOT EXISTS threads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id VARCHAR(255) NOT NULL UNIQUE,
    subject VARCHAR(500),
    sender_email VARCHAR(255) NOT NULL,
    first_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'Open' CHECK (status IN ('Open', 'Resolved', 'Escalated', 'Ignored')),
    assigned_to VARCHAR(255),
    priority VARCHAR(20) DEFAULT 'Medium' CHECK (priority IN ('Critical', 'High', 'Medium', 'Low')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sender_email) REFERENCES contacts(email) ON DELETE RESTRICT
);

CREATE INDEX idx_threads_sender_email ON threads(sender_email);
CREATE INDEX idx_threads_status ON threads(status);
CREATE INDEX idx_threads_priority ON threads(priority DESC);
CREATE INDEX idx_threads_last_updated ON threads(last_updated_at DESC);
CREATE INDEX idx_threads_assigned_to ON threads(assigned_to);

CREATE TRIGGER update_threads_updated_at BEFORE UPDATE ON threads
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- 3. EMAILS TABLE - Individual Email Messages
-- ============================================================================
CREATE TABLE IF NOT EXISTS emails (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID NOT NULL,
    message_id VARCHAR(255) NOT NULL UNIQUE,
    sender VARCHAR(255) NOT NULL,
    recipient VARCHAR(255),
    subject VARCHAR(500),
    body TEXT,
    timestamp TIMESTAMP NOT NULL,
    
    -- Classification & Sentiment Analysis
    category VARCHAR(50) CHECK (category IN (
        'Complaint', 'Inquiry', 'Bug Report', 'Feature Request', 
        'Compliance', 'Legal', 'Billing', 'Spam', 'Internal', 'Other'
    )),
    sentiment VARCHAR(20) CHECK (sentiment IN ('Positive', 'Neutral', 'Negative', 'Mixed')),
    sentiment_score DECIMAL(3, 2) CHECK (sentiment_score BETWEEN -1.00 AND 1.00),
    urgency VARCHAR(20) CHECK (urgency IN ('Critical', 'High', 'Medium', 'Low')),
    confidence DECIMAL(3, 2) CHECK (confidence BETWEEN 0.00 AND 1.00),
    
    -- Processing Status
    requires_human BOOLEAN DEFAULT FALSE,
    status VARCHAR(50) DEFAULT 'Received' CHECK (status IN (
        'Received', 'Processing', 'Replied', 'Escalated', 'Ignored'
    )),
    
    -- Entity Extraction (NER)
    raw_entities JSONB DEFAULT '{}'::jsonb,
    
    -- Metadata
    is_internal BOOLEAN DEFAULT FALSE,
    is_spam BOOLEAN DEFAULT FALSE,
    is_security_alert BOOLEAN DEFAULT FALSE,
    is_legal_threat BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (thread_id) REFERENCES threads(id) ON DELETE CASCADE
);

CREATE INDEX idx_emails_thread_id ON emails(thread_id);
CREATE INDEX idx_emails_sender ON emails(sender);
CREATE INDEX idx_emails_timestamp ON emails(timestamp DESC);
CREATE INDEX idx_emails_category ON emails(category);
CREATE INDEX idx_emails_urgency ON emails(urgency DESC);
CREATE INDEX idx_emails_sentiment ON emails(sentiment_score DESC);
CREATE INDEX idx_emails_status ON emails(status);
CREATE INDEX idx_emails_requires_human ON emails(requires_human) WHERE requires_human = TRUE;
CREATE INDEX idx_emails_is_spam ON emails(is_spam) WHERE is_spam = TRUE;
CREATE INDEX idx_emails_is_security ON emails(is_security_alert) WHERE is_security_alert = TRUE;
CREATE INDEX idx_emails_is_legal ON emails(is_legal_threat) WHERE is_legal_threat = TRUE;

CREATE TRIGGER update_emails_updated_at BEFORE UPDATE ON emails
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- 4. ACTIONS TABLE - Agent Decisions & Responses
-- ============================================================================
CREATE TABLE IF NOT EXISTS actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email_id UUID NOT NULL,
    thread_id UUID NOT NULL,
    
    -- Agent Reasoning
    agent_reasoning_log JSONB DEFAULT '{}'::jsonb,
    agent_model VARCHAR(50),
    reasoning_trace TEXT,
    
    -- Action Details
    action_type VARCHAR(50) NOT NULL CHECK (action_type IN (
        'Auto-Reply', 'Escalate', 'Legal-Flag', 'Security-Flag', 
        'Ticket-Created', 'Ignored', 'Draft-Created', 'Manual-Review'
    )),
    proposed_content TEXT,
    
    -- Approval Workflow
    is_approved BOOLEAN DEFAULT FALSE,
    approved_by VARCHAR(255),
    approved_at TIMESTAMP,
    
    -- Execution
    executed_at TIMESTAMP,
    execution_status VARCHAR(50) CHECK (execution_status IN ('Pending', 'Executed', 'Failed', 'Cancelled')),
    
    -- Policy References (for RAG citations)
    rag_citations JSONB DEFAULT '[]'::jsonb,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (email_id) REFERENCES emails(id) ON DELETE CASCADE,
    FOREIGN KEY (thread_id) REFERENCES threads(id) ON DELETE CASCADE
);

CREATE INDEX idx_actions_email_id ON actions(email_id);
CREATE INDEX idx_actions_thread_id ON actions(thread_id);
CREATE INDEX idx_actions_action_type ON actions(action_type);
CREATE INDEX idx_actions_is_approved ON actions(is_approved) WHERE is_approved = FALSE;
CREATE INDEX idx_actions_execution_status ON actions(execution_status);
CREATE INDEX idx_actions_created_at ON actions(created_at DESC);

CREATE TRIGGER update_actions_updated_at BEFORE UPDATE ON actions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- 5. KNOWLEDGE_CHUNKS TABLE - RAG Vector Store
-- ============================================================================
CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_doc VARCHAR(255) NOT NULL,
    chunk_index INT NOT NULL,
    chunk_text TEXT NOT NULL,
    embedding vector(384),
    token_count INT,
    
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(source_doc, chunk_index)
);

CREATE INDEX idx_knowledge_source_doc ON knowledge_chunks(source_doc);
CREATE INDEX idx_knowledge_embedding ON knowledge_chunks USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE TRIGGER update_knowledge_chunks_updated_at BEFORE UPDATE ON knowledge_chunks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- 6. WEB_INTELLIGENCE_CACHE TABLE - Scraped Public Data
-- ============================================================================
CREATE TABLE IF NOT EXISTS web_intelligence_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_url VARCHAR(500) NOT NULL,
    target_entity VARCHAR(255) NOT NULL,
    source_type VARCHAR(50) CHECK (source_type IN (
        'Trustpilot', 'G2', 'Capterra', 'Competitor', 'Social', 'News'
    )),
    
    scraped_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    scraped_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    
    http_status INT,
    scrape_success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_web_cache_target_entity ON web_intelligence_cache(target_entity);
CREATE INDEX idx_web_cache_source_type ON web_intelligence_cache(source_type);
CREATE INDEX idx_web_cache_expires_at ON web_intelligence_cache(expires_at);
CREATE INDEX idx_web_cache_scraped_at ON web_intelligence_cache(scraped_at DESC);

CREATE TRIGGER update_web_intelligence_cache_updated_at BEFORE UPDATE ON web_intelligence_cache
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- 7. AUDIT_LOG TABLE - Compliance & Audit Trail
-- ============================================================================
CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID NOT NULL,
    action VARCHAR(100) NOT NULL,
    performed_by VARCHAR(255) NOT NULL,
    
    old_values JSONB DEFAULT '{}'::jsonb,
    new_values JSONB DEFAULT '{}'::jsonb,
    
    ip_address VARCHAR(45),
    user_agent TEXT,
    
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_entity ON audit_log(entity_type, entity_id);
CREATE INDEX idx_audit_performed_by ON audit_log(performed_by);
CREATE INDEX idx_audit_timestamp ON audit_log(timestamp DESC);
CREATE INDEX idx_audit_action ON audit_log(action);

-- ============================================================================
-- 8. SENTIMENT_TREND TABLE - Time-series Analytics
-- ============================================================================
CREATE TABLE IF NOT EXISTS sentiment_trend (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sender_email VARCHAR(255) NOT NULL,
    
    date DATE NOT NULL,
    avg_sentiment DECIMAL(3, 2),
    min_sentiment DECIMAL(3, 2),
    max_sentiment DECIMAL(3, 2),
    email_count INT DEFAULT 0,
    
    moving_avg_7d DECIMAL(3, 2),
    moving_avg_30d DECIMAL(3, 2),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(sender_email, date),
    FOREIGN KEY (sender_email) REFERENCES contacts(email) ON DELETE CASCADE
);

CREATE INDEX idx_sentiment_trend_sender ON sentiment_trend(sender_email);
CREATE INDEX idx_sentiment_trend_date ON sentiment_trend(date DESC);
CREATE INDEX idx_sentiment_trend_moving_avg ON sentiment_trend(moving_avg_7d DESC);

CREATE TRIGGER update_sentiment_trend_updated_at BEFORE UPDATE ON sentiment_trend
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- 9. PROCESSING_JOBS TABLE - Async Job Tracking
-- ============================================================================
CREATE TABLE IF NOT EXISTS processing_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email_id UUID NOT NULL,
    job_type VARCHAR(50) NOT NULL,
    
    status VARCHAR(50) DEFAULT 'Pending' CHECK (status IN (
        'Pending', 'Processing', 'Completed', 'Failed', 'Cancelled'
    )),
    
    progress_percentage INT DEFAULT 0,
    error_message TEXT,
    result_data JSONB DEFAULT '{}'::jsonb,
    
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (email_id) REFERENCES emails(id) ON DELETE CASCADE
);

CREATE INDEX idx_processing_jobs_status ON processing_jobs(status);
CREATE INDEX idx_processing_jobs_email_id ON processing_jobs(email_id);
CREATE INDEX idx_processing_jobs_created_at ON processing_jobs(created_at DESC);

CREATE TRIGGER update_processing_jobs_updated_at BEFORE UPDATE ON processing_jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- MATERIALIZED VIEWS - Common Aggregations
-- ============================================================================

-- Daily email stats
CREATE VIEW IF NOT EXISTS email_stats_daily AS
SELECT
    DATE(timestamp) as date,
    COUNT(*) as total_emails,
    SUM(CASE WHEN category = 'Spam' THEN 1 ELSE 0 END) as spam_count,
    SUM(CASE WHEN requires_human = TRUE THEN 1 ELSE 0 END) as requires_human_count,
    SUM(CASE WHEN urgency = 'Critical' THEN 1 ELSE 0 END) as critical_count,
    AVG(sentiment_score) as avg_sentiment,
    AVG(confidence) as avg_confidence
FROM emails
GROUP BY DATE(timestamp)
ORDER BY date DESC;

-- Thread status summary
CREATE VIEW IF NOT EXISTS thread_summary AS
SELECT
    t.id,
    t.thread_id,
    t.sender_email,
    t.status,
    COUNT(e.id) as email_count,
    MAX(e.timestamp) as last_email_at,
    AVG(e.sentiment_score) as avg_sentiment,
    SUM(CASE WHEN e.requires_human = TRUE THEN 1 ELSE 0 END) as human_review_count
FROM threads t
LEFT JOIN emails e ON t.id = e.thread_id
GROUP BY t.id, t.thread_id, t.sender_email, t.status;

-- Churn risk summary
CREATE VIEW IF NOT EXISTS churn_risk_summary AS
SELECT
    c.id,
    c.email,
    c.company,
    c.churn_risk_score,
    COUNT(DISTINCT t.id) as total_threads,
    SUM(CASE WHEN t.status = 'Escalated' THEN 1 ELSE 0 END) as escalated_threads,
    AVG(e.sentiment_score) as avg_sentiment,
    MAX(t.last_updated_at) as last_thread_at
FROM contacts c
LEFT JOIN threads t ON c.email = t.sender_email
LEFT JOIN emails e ON t.id = e.thread_id
WHERE c.status IN ('Active', 'VIP')
GROUP BY c.id, c.email, c.company, c.churn_risk_score
ORDER BY c.churn_risk_score DESC;

-- ============================================================================
-- VERIFY SCHEMA CREATION
-- ============================================================================
SELECT 'Database schema created successfully!' as status;

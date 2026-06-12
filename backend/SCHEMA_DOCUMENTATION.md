# SenAI CRM Intelligence Platform - Database Schema Documentation

## 📊 Database Overview

**Database Name**: `crm_ai`  
**Dialect**: PostgreSQL 17+  
**Total Tables**: 9  
**Total Indexes**: 30+  
**Triggers**: 9 (for auto-updating `updated_at`)  
**Views**: 3 (pre-aggregated analytics)  
**Extensions**: uuid-ossp, pgcrypto, vector (pgvector)

---

## 🗂️ Table Relationships Map

```
┌─────────────────────────────────────────────────────────────────┐
│                         CONTACTS                               │
│  (CRM Profiles: email, company, churn_risk_score)              │
└────┬───────────────────────────────────────────────────────┬───┘
     │                                                         │
     │ sends (FK: sender_email)                      tracks sentiment
     │                                                         │
     ▼                                                         ▼
┌──────────────────────────────────┐              ┌─────────────────┐
│       THREADS                    │              │ SENTIMENT_TREND │
│ (Conversations: thread_id,      │              │ (Time-series)   │
│  status, priority)               │              └─────────────────┘
└────┬────────────────┬────────────┘
     │                │
     │ contains       │ triggers
     │                │
     ▼                ▼
┌──────────────────┐  ┌─────────────────────┐
│    EMAILS        │  │     ACTIONS         │
│ (Messages,       │  │ (Agent decisions,   │
│  sentiment,      │◄─┤  reasoning logs)    │
│  urgency,        │  │                     │
│  category)       │  └────┬────────────┬───┘
└───┬──────────────┘       │            │
    │                      │            │
    │ processed by         │ cites      │ enriches
    │                      │            │
    ▼                      ▼            ▼
┌──────────────────┐  ┌──────────────┐  ┌──────────────────┐
│ PROCESSING_JOBS  │  │ KNOWLEDGE_   │  │ WEB_INTELLIGENCE │
│ (Async tracking) │  │ CHUNKS       │  │ _CACHE           │
└──────────────────┘  │ (RAG vectors)│  │ (Scraped data)   │
                      └──────────────┘  └──────────────────┘

                    ┌──────────────┐
                    │  AUDIT_LOG   │
                    │ (Compliance) │
                    └──────────────┘
```

---

## 📋 Detailed Table Schema

### 1. **CONTACTS** - CRM Profiles
**Purpose**: Store customer/contact information with churn risk scoring

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| `id` | UUID | PK, DEFAULT gen_random_uuid() | Unique identifier |
| `email` | VARCHAR(255) | NOT NULL, UNIQUE | Contact email (primary key) |
| `name` | VARCHAR(255) | | Contact name |
| `company` | VARCHAR(255) | | Company affiliation |
| `status` | VARCHAR(50) | DEFAULT 'Active' | Active\|VIP\|Blocked\|Churned |
| `account_value` | DECIMAL(12,2) | DEFAULT 0.00 | Account value in USD |
| `churn_risk_score` | DECIMAL(3,2) | 0.00-1.00 | Risk score (0=safe, 1=high risk) |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Record creation time |
| `last_contact_at` | TIMESTAMP | | Last email from contact |
| `updated_at` | TIMESTAMP | AUTO via trigger | Last update time |
| `metadata` | JSONB | DEFAULT '{}' | Flexible metadata storage |

**Indexes**: `email`, `status`, `churn_risk_score`, `last_contact_at`  
**Trigger**: `update_contacts_updated_at`

**Use Cases**:
- Find VIP customers: `SELECT * FROM contacts WHERE status = 'VIP'`
- High churn risk: `SELECT * FROM contacts WHERE churn_risk_score > 0.7`
- Inactive contacts: `SELECT * FROM contacts WHERE last_contact_at < NOW() - INTERVAL '30 days'`

---

### 2. **THREADS** - Email Conversation Threads
**Purpose**: Group related emails into conversations

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| `id` | UUID | PK | Internal ID |
| `thread_id` | VARCHAR(255) | UNIQUE | From email-data-advanced.json |
| `subject` | VARCHAR(500) | | Thread subject line |
| `sender_email` | VARCHAR(255) | FK→contacts.email | Who started thread |
| `first_seen_at` | TIMESTAMP | DEFAULT NOW | Thread creation time |
| `last_updated_at` | TIMESTAMP | DEFAULT NOW | Last email in thread |
| `status` | VARCHAR(50) | DEFAULT 'Open' | Open\|Resolved\|Escalated\|Ignored |
| `assigned_to` | VARCHAR(255) | | Assigned team member |
| `priority` | VARCHAR(20) | DEFAULT 'Medium' | Critical\|High\|Medium\|Low |
| `created_at` | TIMESTAMP | DEFAULT NOW | Record creation |
| `updated_at` | TIMESTAMP | AUTO via trigger | Last update |

**Indexes**: `sender_email`, `status`, `priority`, `last_updated_at`, `assigned_to`  
**Trigger**: `update_threads_updated_at`

**Use Cases**:
- Get all threads for a contact: `SELECT * FROM threads WHERE sender_email = 'bob@example.com'`
- Get escalated threads: `SELECT * FROM threads WHERE status = 'Escalated'`
- Threads needing attention: `SELECT * FROM threads WHERE priority = 'Critical' AND status != 'Resolved'`

---

### 3. **EMAILS** - Individual Email Messages
**Purpose**: Store individual emails with AI classification

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| `id` | UUID | PK | Email ID |
| `thread_id` | UUID | FK→threads.id | Thread grouping |
| `message_id` | VARCHAR(255) | UNIQUE | From JSON dataset (idempotency key) |
| `sender` | VARCHAR(255) | | Email sender |
| `recipient` | VARCHAR(255) | | Email recipient |
| `subject` | VARCHAR(500) | | Subject line |
| `body` | TEXT | | Email body |
| `timestamp` | TIMESTAMP | NOT NULL | When email arrived |
| **Classification** | | | |
| `category` | VARCHAR(50) | CHECK enum | Complaint\|Inquiry\|Bug Report\|Feature Request\|Compliance\|Legal\|Billing\|Spam\|Internal\|Other |
| `sentiment` | VARCHAR(20) | CHECK enum | Positive\|Neutral\|Negative\|Mixed |
| `sentiment_score` | DECIMAL(3,2) | -1.00 to 1.00 | Numeric sentiment |
| `urgency` | VARCHAR(20) | CHECK enum | Critical\|High\|Medium\|Low |
| `confidence` | DECIMAL(3,2) | 0.00-1.00 | Classification confidence |
| **Processing** | | | |
| `requires_human` | BOOLEAN | DEFAULT FALSE | Flag for human review |
| `status` | VARCHAR(50) | CHECK enum | Received\|Processing\|Replied\|Escalated\|Ignored |
| `raw_entities` | JSONB | | NER: order_ids, ticket_ids, amounts, deadlines |
| **Metadata** | | | |
| `is_internal` | BOOLEAN | DEFAULT FALSE | Internal email flag |
| `is_spam` | BOOLEAN | DEFAULT FALSE | Spam flag |
| `is_security_alert` | BOOLEAN | DEFAULT FALSE | Security threat flag |
| `is_legal_threat` | BOOLEAN | DEFAULT FALSE | Legal threat flag |
| `created_at` | TIMESTAMP | | Record creation |
| `updated_at` | TIMESTAMP | AUTO via trigger | Last update |

**Indexes**: `thread_id`, `sender`, `timestamp`, `category`, `urgency`, `sentiment_score`, `status`, and partial indexes for flags  
**Trigger**: `update_emails_updated_at`

**Use Cases**:
- Get critical emails: `SELECT * FROM emails WHERE urgency = 'Critical' AND requires_human = FALSE`
- Spam filtering: `SELECT * FROM emails WHERE is_spam = TRUE`
- Security alerts: `SELECT * FROM emails WHERE is_security_alert = TRUE`
- Low-confidence classifications: `SELECT * FROM emails WHERE confidence < 0.7`

---

### 4. **ACTIONS** - Agent Decisions & Responses
**Purpose**: Store agent reasoning and proposed actions

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| `id` | UUID | PK | Action ID |
| `email_id` | UUID | FK→emails.id | Which email triggered action |
| `thread_id` | UUID | FK→threads.id | Thread context |
| `agent_reasoning_log` | JSONB | | Full reasoning trace (Thought→Action→Observation) |
| `agent_model` | VARCHAR(50) | | LLM model used (e.g., 'gemini-2.0-pro') |
| `reasoning_trace` | TEXT | | Human-readable trace |
| `action_type` | VARCHAR(50) | CHECK enum | Auto-Reply\|Escalate\|Legal-Flag\|Security-Flag\|Ticket-Created\|Ignored\|Draft-Created\|Manual-Review |
| `proposed_content` | TEXT | | Draft reply or action description |
| `is_approved` | BOOLEAN | DEFAULT FALSE | Awaiting approval? |
| `approved_by` | VARCHAR(255) | | Who approved (user_id or 'system') |
| `approved_at` | TIMESTAMP | | When approved |
| `executed_at` | TIMESTAMP | | When executed |
| `execution_status` | VARCHAR(50) | CHECK enum | Pending\|Executed\|Failed\|Cancelled |
| `rag_citations` | JSONB | | Array of {source_doc, chunk_id, score} for RAG policy references |
| `created_at` | TIMESTAMP | | Creation time |
| `updated_at` | TIMESTAMP | AUTO via trigger | Last update |

**Indexes**: `email_id`, `thread_id`, `action_type`, `is_approved`, `execution_status`, `created_at`  
**Trigger**: `update_actions_updated_at`

**Use Cases**:
- Get unapproved actions: `SELECT * FROM actions WHERE is_approved = FALSE ORDER BY created_at`
- Failed executions: `SELECT * FROM actions WHERE execution_status = 'Failed'`
- Get agent reasoning: `SELECT agent_reasoning_log FROM actions WHERE action_type = 'Escalate'`

---

### 5. **KNOWLEDGE_CHUNKS** - RAG Vector Store
**Purpose**: Store chunked policy documents with embeddings for retrieval

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| `id` | UUID | PK | Chunk ID |
| `source_doc` | VARCHAR(255) | | Document name (e.g., 'pricing_policy.md') |
| `chunk_index` | INT | | Chunk sequence number |
| `chunk_text` | TEXT | | 300-500 token text chunk |
| `embedding` | vector(384) | | 384-dim embedding (sentence-transformers) |
| `token_count` | INT | | Tokens in this chunk |
| `metadata` | JSONB | | {page, section, created_date} |
| `created_at` | TIMESTAMP | | When loaded |
| `updated_at` | TIMESTAMP | AUTO via trigger | When updated |

**Indexes**: `source_doc`, IVFFlat index on `embedding` (384-dim cosine)  
**Unique Constraint**: (source_doc, chunk_index)  
**Trigger**: `update_knowledge_chunks_updated_at`

**Use Cases**:
- Load pricing policy: `INSERT INTO knowledge_chunks VALUES (...)`
- Vector search: `SELECT chunk_text, similarity FROM knowledge_chunks WHERE embedding <-> $1 LIMIT 3`
- Find all chunks from a document: `SELECT * FROM knowledge_chunks WHERE source_doc = 'refund_policy.md'`

---

### 6. **WEB_INTELLIGENCE_CACHE** - Scraped Public Data
**Purpose**: Cache scraped reputation data (G2, Trustpilot) for 6 hours

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| `id` | UUID | PK | Cache entry ID |
| `source_url` | VARCHAR(500) | | URL scraped |
| `target_entity` | VARCHAR(255) | | Company/product name |
| `source_type` | VARCHAR(50) | CHECK enum | Trustpilot\|G2\|Capterra\|Competitor\|Social\|News |
| `scraped_data` | JSONB | | {rating, review_count, recent_mentions, sentiment_summary} |
| `scraped_at` | TIMESTAMP | | When scraped |
| `expires_at` | TIMESTAMP | | 6-hour TTL |
| `http_status` | INT | | HTTP status code |
| `scrape_success` | BOOLEAN | DEFAULT TRUE | Scrape successful? |
| `error_message` | TEXT | | Error details if failed |
| `created_at` | TIMESTAMP | | Record creation |
| `updated_at` | TIMESTAMP | AUTO via trigger | Last update |

**Indexes**: `target_entity`, `source_type`, `expires_at`, `scraped_at`  
**Trigger**: `update_web_intelligence_cache_updated_at`

**Use Cases**:
- Get cached G2 rating: `SELECT scraped_data FROM web_intelligence_cache WHERE source_type = 'G2' AND expires_at > NOW()`
- Expired cache cleanup: `DELETE FROM web_intelligence_cache WHERE expires_at < NOW()`
- Failed scrapes: `SELECT * FROM web_intelligence_cache WHERE scrape_success = FALSE`

---

### 7. **AUDIT_LOG** - Compliance & Audit Trail
**Purpose**: Immutable log of all changes for compliance

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| `id` | UUID | PK | Log entry ID |
| `entity_type` | VARCHAR(50) | | 'email', 'thread', 'action', 'contact' |
| `entity_id` | UUID | | ID of entity that changed |
| `action` | VARCHAR(100) | | 'INSERT', 'UPDATE', 'DELETE', 'APPROVED', 'EXECUTED' |
| `performed_by` | VARCHAR(255) | | 'system', 'user_id', or 'agent' |
| `old_values` | JSONB | | Previous state |
| `new_values` | JSONB | | New state |
| `ip_address` | VARCHAR(45) | | IPv4 or IPv6 |
| `user_agent` | TEXT | | Browser/client info |
| `timestamp` | TIMESTAMP | DEFAULT NOW | When changed |

**Indexes**: `entity_type+entity_id`, `performed_by`, `timestamp`, `action`

**Use Cases**:
- Get all changes to an email: `SELECT * FROM audit_log WHERE entity_type = 'email' AND entity_id = $1 ORDER BY timestamp`
- Track approvals: `SELECT * FROM audit_log WHERE action = 'APPROVED' ORDER BY timestamp DESC`
- GDPR data export: `SELECT * FROM audit_log WHERE entity_id IN (SELECT id FROM contacts WHERE email = $1)`

---

### 8. **SENTIMENT_TREND** - Time-Series Analytics
**Purpose**: Pre-aggregated sentiment data for fast dashboard queries

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| `id` | UUID | PK | Trend entry ID |
| `sender_email` | VARCHAR(255) | FK→contacts.email | Contact email |
| `date` | DATE | | Date |
| `avg_sentiment` | DECIMAL(3,2) | | Daily average sentiment |
| `min_sentiment` | DECIMAL(3,2) | | Lowest sentiment that day |
| `max_sentiment` | DECIMAL(3,2) | | Highest sentiment that day |
| `email_count` | INT | DEFAULT 0 | How many emails that day |
| `moving_avg_7d` | DECIMAL(3,2) | | 7-day moving average |
| `moving_avg_30d` | DECIMAL(3,2) | | 30-day moving average |
| `created_at` | TIMESTAMP | | Created |
| `updated_at` | TIMESTAMP | AUTO via trigger | Updated |

**Indexes**: `sender_email`, `date`, `moving_avg_7d`  
**Unique Constraint**: (sender_email, date)  
**Trigger**: `update_sentiment_trend_updated_at`

**Use Cases**:
- Detect churn risk: `SELECT * FROM sentiment_trend WHERE moving_avg_7d < -0.5 ORDER BY date DESC`
- Dashboard query: `SELECT * FROM sentiment_trend WHERE sender_email = $1 AND date >= NOW() - INTERVAL '30 days'`

---

### 9. **PROCESSING_JOBS** - Async Job Tracking
**Purpose**: Track background processing jobs (LLM classification, web scraping)

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| `id` | UUID | PK | Job ID |
| `email_id` | UUID | FK→emails.id | Which email |
| `job_type` | VARCHAR(50) | | 'classify_email', 'scrape_reputation', 'generate_rag_embedding' |
| `status` | VARCHAR(50) | DEFAULT 'Pending' | Pending\|Processing\|Completed\|Failed\|Cancelled |
| `progress_percentage` | INT | DEFAULT 0 | 0-100% |
| `error_message` | TEXT | | Error details if failed |
| `result_data` | JSONB | | {classification_result, embedding_model_version} |
| `started_at` | TIMESTAMP | | When job started |
| `completed_at` | TIMESTAMP | | When job finished |
| `created_at` | TIMESTAMP | | Job creation time |
| `updated_at` | TIMESTAMP | AUTO via trigger | Last status update |

**Indexes**: `status`, `email_id`, `created_at`  
**Trigger**: `update_processing_jobs_updated_at`

**Use Cases**:
- Get pending jobs: `SELECT * FROM processing_jobs WHERE status = 'Pending' ORDER BY created_at LIMIT 10`
- Monitor progress: `SELECT email_id, progress_percentage FROM processing_jobs WHERE job_type = 'classify_email'`
- Failed job analysis: `SELECT * FROM processing_jobs WHERE status = 'Failed' AND created_at > NOW() - INTERVAL '24 hours'`

---

## 📊 Pre-Built Views (Analytics)

### View 1: `email_stats_daily`
**Purpose**: Daily email statistics for dashboard

```sql
SELECT 
    date,                 -- DATE
    total_emails,         -- Count of all emails
    spam_count,          -- Spam filtered
    requires_human_count, -- Escalated to human
    critical_count,      -- Critical urgency
    avg_sentiment,       -- Average sentiment that day
    avg_confidence       -- Average classification confidence
FROM email_stats_daily
ORDER BY date DESC;
```

### View 2: `thread_summary`
**Purpose**: Thread-level aggregations

```sql
SELECT 
    id, thread_id, sender_email,
    status,
    email_count,        -- Emails in thread
    last_email_at,      -- When thread was last active
    avg_sentiment,      -- Thread sentiment average
    human_review_count  -- How many emails need human review
FROM thread_summary;
```

### View 3: `churn_risk_summary`
**Purpose**: Customers at risk of churning

```sql
SELECT 
    id, email, company,
    churn_risk_score,   -- 0.00-1.00
    total_threads,
    escalated_threads,
    avg_sentiment,      -- Are they negative?
    last_thread_at
FROM churn_risk_summary
ORDER BY churn_risk_score DESC;
```

---

## 🔑 Key Design Decisions

| Decision | Why |
|----------|-----|
| **UUIDs instead of INT** | Distributed system friendly, secure, no collisions |
| **JSONB for flexible fields** | NER entities, reasoning logs, metadata—schema evolution |
| **Vector(384) embeddings** | sentence-transformers standard size; fast similarity search |
| **IVFFlat index** | Fast approximate nearest neighbor search for RAG |
| **Partial indexes** (is_spam, is_security) | Only index true values; save space |
| **Triggers for updated_at** | PostgreSQL-native solution (not MySQL ON UPDATE) |
| **6-hour TTL on web cache** | Avoid rate-limiting; balance freshness with performance |
| **Audit log immutable** | INSERT-only; never delete; GDPR compliance |
| **Moving averages pre-computed** | Fast dashboard loads; denormalized for speed |

---

## 📈 Performance SLAs

| Query | SLA | Technique |
|-------|-----|-----------|
| Get full thread (<50 emails) | <100ms | `thread_id` index + FK |
| Sentiment trend (30 days) | <200ms | `sentiment_trend.date` index |
| Vector similarity search (top-3) | <200ms | IVFFlat index on embeddings |
| Email stats daily | <500ms | Pre-aggregated view |
| Find escalated threads | <100ms | `status` partial index |
| Find critical emails | <50ms | `urgency + requires_human` index |

---

## 🚀 Next Steps

1. **Load the schema**: 
   ```powershell
   psql -U postgres -d crm_ai -f "backend/database_schema.sql"
   ```

2. **Verify tables were created**:
   ```sql
   \dt
   \dv
   ```

3. **Insert sample data** (optional):
   ```sql
   INSERT INTO contacts (email, name, company, account_value, churn_risk_score)
   VALUES ('alice@example.com', 'Alice', 'Acme Corp', 5000.00, 0.2);
   ```

4. **Test a query**:
   ```sql
   SELECT * FROM contacts LIMIT 5;
   ```

---

## 📚 Additional Resources

- **pgvector docs**: https://github.com/pgvector/pgvector
- **PostgreSQL JSON**: https://www.postgresql.org/docs/17/datatype-json.html
- **Index strategy**: https://www.postgresql.org/docs/17/indexes.html

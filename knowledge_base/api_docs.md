# SenAI API Documentation

## Base URL
```
https://api.senai.io/v1
```

## Authentication

All requests require API key in header:
```
Authorization: Bearer YOUR_API_KEY
```

## Rate Limits

| Plan | Requests/min | Requests/day |
|------|-------------|------------|
| Starter | 100 | 100K |
| Professional | 1000 | 1M |
| Enterprise | 10000 | Unlimited |

## Endpoints

### 1. Email Ingestion

**POST /emails/ingest**

Ingest a new email into the system.

Request:
```json
{
  "message_id": "msg_001",
  "sender": "customer@example.com",
  "subject": "Bug in checkout",
  "body": "...",
  "timestamp": "2026-06-11T10:30:00Z",
  "thread_id": "thread_123"
}
```

Response (201 Created):
```json
{
  "email_id": "email_uuid_001",
  "status": "processed",
  "classification": {
    "category": "Bug Report",
    "urgency": "High",
    "sentiment": "Negative",
    "confidence": 0.95
  },
  "requires_human_review": false
}
```

### 2. Thread Retrieval

**GET /threads/{contact_email}**

Get all emails in a conversation thread.

Response:
```json
{
  "contact_email": "customer@example.com",
  "thread_count": 3,
  "emails": [
    {
      "message_id": "msg_001",
      "subject": "Initial inquiry",
      "timestamp": "2026-06-10T09:00:00Z",
      "category": "Inquiry",
      "sentiment": "Neutral"
    }
  ],
  "sentiment_trend": "Negative (trending)",
  "last_message": "2026-06-11T10:30:00Z"
}
```

### 3. Analytics

**GET /analytics/sentiment-trend**

Get sentiment trends for churn detection.

Query params:
- `days`: 7 (default), 30, 90
- `category`: Optional filter

Response:
```json
{
  "period": "7_days",
  "accounts": [
    {
      "contact_email": "customer@example.com",
      "avg_sentiment": -0.65,
      "trend": "declining",
      "churn_risk": "high",
      "recent_emails": 5,
      "last_activity": "2026-06-11T10:30:00Z"
    }
  ]
}
```

### 4. Knowledge Base Search

**POST /knowledge/search**

Search relevant policies and documentation.

Request:
```json
{
  "query": "What is the refund policy for annual plans?",
  "top_k": 3
}
```

Response:
```json
{
  "results": [
    {
      "score": 0.92,
      "document": "refund_policy.md",
      "section": "Annual Plan Cancellation",
      "content": "..."
    }
  ]
}
```

### 5. Agent Dry Run

**POST /agent/dry-run**

Test agent reasoning on an email without executing actions.

Request:
```json
{
  "email_id": "email_uuid_001",
  "max_steps": 6
}
```

Response:
```json
{
  "reasoning": [
    {
      "step": 1,
      "thought": "Customer reports bug in checkout...",
      "action": "search_knowledge_base",
      "observation": "Found 2 related bug fixes"
    }
  ],
  "recommended_action": "escalate_to_human",
  "confidence": 0.89
}
```

## Error Responses

All errors return standard format:

```json
{
  "error": "invalid_request",
  "message": "Missing required field: sender",
  "status": 400,
  "request_id": "req_xyz"
}
```

### Common Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request |
| 401 | Unauthorized |
| 429 | Rate Limited |
| 500 | Server Error |

## Webhooks

Register webhook to receive events:

**POST /webhooks/register**

```json
{
  "event_type": "email.received",
  "url": "https://yourdomain.com/webhook",
  "active": true
}
```

Events fired:
- `email.received` - New email ingested
- `email.classified` - Classification complete
- `email.escalated` - Escalated to human
- `email.replied` - Auto-reply sent

## SDK

Available in Python, Node.js, Go, Ruby

```python
import senai

client = senai.Client(api_key="your_key")
result = client.emails.ingest(message_id="msg_001", sender="...", ...)
```

## Best Practices

1. Use batch endpoints for >10 emails
2. Implement exponential backoff on 429 errors
3. Cache knowledge base searches (results valid 1 hour)
4. Use webhooks instead of polling
5. Include request IDs in error logs

## Support

- Documentation: https://docs.senai.io
- Status Page: https://status.senai.io
- Email: api-support@senai.io

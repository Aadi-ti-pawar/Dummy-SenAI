# SenAI Escalation Matrix

## Escalation Decision Tree

### Level 1: Auto-Respond (No Human)

**Trigger Conditions:**
- Category: Inquiry + Sentiment: Positive/Neutral
- Confidence: >0.90
- No legal/security flags
- Not recurring issue for same contact

**Auto-response Template:**
```
Thank you for contacting SenAI. Your inquiry has been received and categorized.

Category: [CATEGORY]
Reference: [EMAIL_ID]

We will respond within 24 hours.
```

**Examples:**
- Pricing inquiry with positive tone
- General how-to question
- Feature request from satisfied customer

---

### Level 2: Tier 1 Support (Standard Queue)

**Trigger Conditions:**
- Category: Inquiry + Sentiment: Negative
- Category: Bug Report + Urgency: Medium/Low
- Category: Billing + Confidence: >0.80
- No legal/security flags

**SLA Response Time:** 2-8 hours

**Responsibilities:**
- Acknowledge receipt
- Provide knowledge base answer if applicable
- Escalate to Tier 2 if unresolved

**Examples:**
- Complaint about documentation
- Minor bug report
- Billing question with dissatisfaction
- Feature request from at-risk customer

---

### Level 3: Tier 2 Support + Product (High Priority)

**Trigger Conditions:**
- Category: Bug Report + Urgency: High
- Category: Feature Request + Contact Value: Enterprise
- Sentiment: Negative + Thread: 3+ emails
- SLA Breach: Previous response missed

**SLA Response Time:** 1-2 hours

**Responsibilities:**
- Immediate investigation
- Provide temporary workaround if applicable
- Engage product team if needed
- Provide detailed status update hourly

**Examples:**
- Critical bug in production
- Enterprise customer with feature urgent need
- Churn risk detected (3+ negative emails)
- SLA miss escalation

---

### Level 4: Executive + Legal Review

**Trigger Conditions (ANY match):**
- **Legal Threat Detected:**
  - Keywords: lawsuit, legal action, court, attorney, damages
  - Confidence: >0.70
  
- **Security Alert:**
  - Keywords: ransomware, hacked, breach, stolen data
  - Account compromised flag: True
  
- **Regulatory/Compliance:**
  - Keywords: GDPR, HIPAA, SOC 2, audit, compliance
  - Category: Compliance
  
- **High-Value Account Churn:**
  - Account ARR: >$50K
  - Sentiment Trend: Negative for 7+ days
  - Churn risk: Critical
  
- **Public Escalation:**
  - Customer threatening public review
  - Social media escalation detected
  - PR risk: High

- **Billing Dispute:**
  - Chargeback filed
  - Amount: >$10K
  - Fraud indicator: Possible

**SLA Response Time:** 30 minutes (24/7)

**Escalation Path:**
1. Immediately flag to Support Manager
2. Loop in Legal (if legal threat)
3. Loop in Product VP (if security)
4. Loop in Founder/CEO (if churn risk >$50K)
5. Create incident ticket in Jira
6. Assign dedicated point person

**Prohibited Actions:**
- Do NOT auto-reply
- Do NOT promise refunds
- Do NOT admit liability
- Do NOT discuss with other customers

**Actions Required:**
- Acknowledge within 15 minutes
- Provide interim response within 30 minutes
- Coordinate legal/product response within 2 hours
- Document all communications
- Follow up every 4 hours until resolved

**Examples:**
- "I'm contacting my lawyer about this breach"
- Customer with 90-day declining sentiment threatening G2 review
- GDPR data export request with threat
- "Our company is switching to competitor unless you fix this today"
- Ransomware attack on customer's infrastructure correlated with our service

---

## Escalation Rules

### By Sentiment
| Sentiment | Action |
|-----------|--------|
| Positive | Auto-respond or Tier 1 |
| Neutral | Tier 1 (if question), Tier 2 (if complaint) |
| Negative (once) | Tier 1 with empathy |
| Negative (2+) | Tier 2 |
| Negative (3+) + Churn risk | Executive review |

### By Urgency
| Urgency | SLA | Escalation |
|---------|-----|-----------|
| Low | 24h | Tier 1 |
| Medium | 8h | Tier 1 |
| High | 2h | Tier 2 |
| Critical | 30min | Executive |

### By Category
| Category | Default Level | Exception |
|----------|---------------|-----------|
| Inquiry | Tier 1 | If negative sentiment → Tier 2 |
| Bug Report | Tier 1 | If High urgency → Tier 2 |
| Billing | Tier 1 | If chargeback → Executive |
| Compliance | Executive | All cases |
| Legal | Executive | All cases |

### Confidence Thresholds
- **High (>0.90):** Tier 1 OK for non-critical
- **Medium (0.70-0.90):** Route to Tier 2 for safety
- **Low (<0.70):** Always escalate to human

---

## Escalation Criteria - When in Doubt

**Always escalate to Executive if:**
1. Customer mentions lawsuit/legal action
2. Security/data breach suspected
3. Account value >$50K and churn risk
4. Multiple unresolved issues (3+ tickets)
5. Your confidence is <0.60
6. Customer demands manager/executive
7. Issue involves compliance/regulation
8. Pattern indicates systemic problem

---

## Contact Routing

| Level | Contact | Channel | Availability |
|-------|---------|---------|--------------|
| Tier 1 Support | support@senai.io | Email/Chat | 9am-6pm PT |
| Tier 2 Support | tier2-support@senai.io | Email/Phone | 9am-6pm PT |
| On-Call Manager | oncall@senai.io | Phone/Email | 24/7 |
| Executive | executive@senai.io | Phone/Email | 24/7 |
| Legal | legal@senai.io | Email | 24/7 (monitored) |

---

## Escalation Workflow

```
Customer Email Received
    ↓
[Heuristic + AI Classification]
    ↓
Confidence >0.90? → Auto-respond
    ↓
Legal/Security Flags? → Executive (Level 4)
    ↓
Urgency Critical? → Tier 2 (Level 3)
    ↓
Sentiment Negative? → Tier 2 (Level 3)
    ↓
Default → Tier 1 (Level 2)
```

---

## De-escalation

**When to de-escalate back to Tier 1:**
- Issue resolved to customer satisfaction
- Follow-up only required for next steps
- No systemic risk
- Customer satisfied

**Action:** Close ticket, add resolution notes, enable Tier 1 to monitor follow-up.

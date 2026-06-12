# SenAI Compliance FAQ

## Data Privacy

**Q: Where is my data stored?**
A: Customer data is stored in AWS data centers in US (N. Virginia, Oregon) or EU (Ireland) based on your location. Data never leaves selected region.

**Q: Is data encrypted?**
A: Yes. All data encrypted in transit (TLS 1.3) and at rest (AES-256). Encryption keys managed by AWS KMS.

**Q: What happens to my data if I delete my account?**
A: Data deleted within 30 days. You can request immediate deletion via GDPR data removal endpoint.

**Q: How long do you retain data?**
A: Starter: 30 days, Professional: 90 days, Enterprise: Custom. Automatic deletion after retention period.

## GDPR Compliance

**Q: Are you GDPR compliant?**
A: Yes. We are a GDPR-compliant Data Processor. DPA signed with all customers.

**Q: How do I exercise my data subject rights?**
A: Submit requests via /dpa/subject-access-request endpoint. Response within 15 days.

**Q: Can I request data portability?**
A: Yes. Full data export available in JSON/CSV format via dashboard. Or API: GET /dpa/data-export

**Q: What about cookie consent?**
A: We use only essential cookies. No tracking cookies. Cookie consent not required (but recommended).

**Q: Do you store data in non-EU locations?**
A: Only if you're a US customer. EU customers data stays in EU per GDPR requirements.

## SOC 2 & Security

**Q: Are you SOC 2 Type II certified?**
A: Yes, certified as of March 2025. Valid until March 2026. Certificate available upon request.

**Q: What security certifications do you have?**
A: SOC 2 Type II, ISO 27001 (in progress), HIPAA (available for Enterprise).

**Q: Do you perform penetration testing?**
A: Yes, annually by third-party firm. Bug bounty program active via HackerOne.

**Q: What about API security?**
A: All APIs use OAuth 2.0, API key rotation enforced every 90 days, Rate limiting + DDoS protection via Cloudflare.

## Compliance Standards

**Q: Are you HIPAA compliant?**
A: HIPAA Business Associate Agreement available for Enterprise customers.

**Q: Do you support FedRAMP?**
A: Not currently. Government customers should contact sales@senai.io

**Q: What about PCI DSS?**
A: We don't store credit cards. Payment processing via Stripe (PCI DSS Level 1).

**Q: Are you CCPA compliant?**
A: Yes. California customers have right to know, delete, opt-out. Available via /ccpa endpoints.

**Q: What about GLBA (financial data)?**
A: Yes, compliant for financial services customers. Requires signed GLBA addendum.

## Data Residency

**Q: Can I choose where my data is stored?**
A: Yes. Available regions: US (Ohio, N. Virginia, Oregon), EU (Ireland, Frankfurt), APAC (Singapore, Sydney).

**Q: Can I have data in multiple regions?**
A: Yes, Enterprise plans can enable multi-region replication for HA.

**Q: What about data sovereignty?**
A: Data stored only in selected region. No automatic cross-region replication unless explicitly enabled.

## Audit & Compliance Reporting

**Q: Can I audit your system?**
A: Yes. Enterprise customers can request audit logs. Available via /audit/logs endpoint.

**Q: Do you provide compliance reports?**
A: Yes. SOC 2 report, DPA, security assessment available upon request for verified customers.

**Q: How do I report a security issue?**
A: Email security@senai.io with details. Do not disclose publicly. Response within 24 hours.

## Sub-processors

**Q: Who are your sub-processors?**
A: AWS (hosting), Stripe (payments), Twilio (SMS), SendGrid (email). Full list at /dpa/sub-processors

**Q: Can I object to sub-processors?**
A: Yes, within 30 days of notice. Submit objection via /dpa/objection endpoint.

**Q: Are sub-processors also compliant?**
A: Yes, all sub-processors SOC 2 Type II or equivalent certified.

## Data Breach Notification

**Q: What if there's a data breach?**
A: We notify affected customers within 48 hours. Notification includes: nature of breach, data affected, remediation steps.

**Q: Do you notify regulators?**
A: Yes, automatically if required by law. We handle GDPR notifications to authorities.

## Right to Audit

**Q: Can I audit your security practices?**
A: Yes. Enterprise customers receive annual security audit summary. On-site audits by arrangement.

**Q: How often do you conduct security audits?**
A: Externally: Annually. Internally: Quarterly. Penetration testing: Annually by third-party.

## Contact

Questions about compliance?
- Email: compliance@senai.io
- DPA requests: dpa-team@senai.io
- Security concerns: security@senai.io
- Response time: 24 hours

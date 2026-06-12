# SenAI Service Level Agreement (SLA)

## Uptime Guarantee

### Starter & Professional Plans
- Uptime SLA: 99.5%
- Maximum downtime: 3.6 hours per month
- Measured across all regions

### Enterprise Plan
- Uptime SLA: 99.95%
- Maximum downtime: 22 minutes per month
- Measured per region with failover guarantee
- Dedicated infrastructure option available

## Excluded Downtime

The following are NOT counted against SLA:
- Scheduled maintenance (24h notice provided)
- Customer-caused issues (misconfiguration, API misuse)
- DDoS attacks or security incidents
- Third-party service failures (AWS, Stripe)
- Force majeure events
- Beta features or preview services

## Support Response Times

### Starter Plan
- Critical (system down): 24 hours
- High (feature broken): 48 hours
- Medium (degraded performance): 5 business days
- Low (general inquiry): 10 business days

### Professional Plan
- Critical: 2 hours
- High: 8 hours
- Medium: 1 business day
- Low: 2 business days

### Enterprise Plan
- Critical: 30 minutes (24/7)
- High: 1 hour (24/7)
- Medium: 4 hours (business hours)
- Low: 1 business day

## Incident Management

- Incident acknowledgment: Within SLA response time
- Status updates: Every 1 hour for critical incidents
- Post-incident report: Within 24 hours of resolution
- Root cause analysis: Within 5 business days

## Service Credits

If SLA is breached:
- 99.0-99.49% uptime: 10% monthly credit
- 98.0-98.99% uptime: 25% monthly credit
- 95.0-97.99% uptime: 50% monthly credit
- <95% uptime: 100% monthly credit + option to cancel without penalty

Credits applied to next billing cycle automatically.

## Data Backup & Recovery

- Real-time replication across 3 geographic regions
- Automatic backup every 1 hour
- Recovery time objective (RTO): 15 minutes
- Recovery point objective (RPO): 5 minutes
- Disaster recovery drills: Quarterly

## Performance Metrics

### API Response Time
- P99: <200ms
- P95: <100ms
- P50: <50ms

### Email Processing Latency
- Classification: <2 seconds per email
- Context retrieval: <500ms
- Response generation: <10 seconds

## Termination for SLA Breaches

If SLA breached for 3 consecutive months:
- Customer may terminate contract without penalty
- Transition support: 30 days free
- Full data export included

## SLA Exceptions

SLA does not apply to:
- Services in beta or preview
- Services with different SLA published
- Free tier or trial accounts

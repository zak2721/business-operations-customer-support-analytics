# Executive Summary

> **Data notice:** all figures are computed from a synthetic dataset generated for this portfolio project (seeded, reproducible). They demonstrate the analytical method and are not real company results.

_Period: Jan 2023 - Dec 2025 · snapshot 31 Dec 2025 · generated 2026-10-30_

## Headline KPIs

| KPI | Value |
|---|---|
| Total Tickets | 24,000 |
| Open Tickets | 257 |
| Avg First Response Time (h) | 5.76 |
| Avg Resolution Time (h) | 34.46 |
| SLA Compliance Rate (%) | 72.91 |
| First Contact Resolution Rate (%) | 21.49 |
| Avg Customer Satisfaction (1-5) | 3.75 |
| Customer Satisfaction Rate (%) | 63.36 |
| Operational Success Rate (%) | 98.00 |
| Total Operational Cost ($) | 11,944,594.04 |
| Avg Cost per Transaction ($) | 0.80 |
| Cost per Resolved Ticket ($) | 479.98 |

## Year over year

| Year | tickets | avg_frt_h | avg_resolution_h | sla_compliance_pct | fcr_pct | avg_csat |
|---|---:|---:|---:|---:|---:|---:|
| 2023 | 7,226.00 | 5.76 | 32.03 | 75.45 | 21.82 | 3.77 |
| 2024 | 8,071.00 | 5.77 | 33.48 | 73.96 | 21.89 | 3.77 |
| 2025 | 8,703.00 | 5.75 | 37.47 | 69.74 | 20.82 | 3.72 |

## What needs attention

1. **Asynchronous channels respond in hours, real-time channels in minutes.** Average first response time is 13.47 h on Web Portal, 10.29 h on Email and 7.53 h on Social Media, versus 5 min on Phone and 8 min on Live Chat. SLA compliance follows the same split: 58.5-65.3% for asynchronous channels vs 84.3-86.0% for real-time.
2. **Satisfaction declines steadily as first response time grows.** Average CSAT is 4.14 when the first response arrives within 15 minutes, 3.50 at 4-8 hours and 2.95 after 24 hours (satisfied share 79.9% -> 29.0%).
3. **An SLA breach is the strongest measured driver of an unhappy customer.** 84.3% of customers whose ticket was resolved within SLA were satisfied (CSAT 4-5), versus 17.9% when the SLA was breached (avg CSAT 4.19 vs 2.79).
4. **Billing & Accounts SLA compliance collapsed in 2025.** Billing SLA compliance fell from 82.86% (2024) to 60.08% (2025), a 22.78-point drop. Billing ticket volume rose from 1,479 to 2,138 (+44.6%) while assignments per active Billing agent rose from 15.1 to 24.9 per month. 2 Billing agents are recorded as terminated.
5. **Returns & Refunds has the weakest service performance of any department.** Returns & Refunds resolves only 50.0% of tickets within SLA (company 72.9%), has the longest average resolution time (59.8 h) and the highest reopen rate (14.6%).
6. **Junior agents breach SLA and get reopened far more often.** Junior agents meet SLA on 53.2% of tickets vs 80.4% for Leads; their reopen rate is 16.6% vs 5.7% and average CSAT 3.41 vs 3.88.
7. **Critical tickets have the lowest SLA compliance.** Only 54.7% of Critical tickets are resolved within their 8-hour SLA, versus 78.3% of Low-priority tickets within 72 hours. Critical tickets are escalated 18.9% of the time.
8. **Refund Approval is the most failure-prone process and is getting worse.** Refund Approval's failure rate rose from 7.06% (2023) to 10.23% (2025), about 5.1x the company average; 89.4% of its operating days were 'Degraded' or 'Critical'.
9. **Payment Reconciliation failures jumped after April 2025 and its unit cost is rising fastest.** Failure rate was 3.18% before April 2025 and 5.90% after. Its cost per transaction grew 12.0% between 2023 and 2025, the highest of any process.

## Recommended next steps

- Introduce an auto-acknowledgement + triage rule for Email/Web Portal, set a 4-hour first-response target for those queues, and route simple categories (Account Access, Order Status, Product Inquiry) to live chat or self-service.
- Publish FRT targets per priority (Critical 1 h, High 4 h, Medium 8 h, Low 24 h) on the team dashboard and alert supervisors when a ticket approaches its FRT target.
- Make SLA compliance the primary team KPI and add an 'SLA at risk' queue (tickets at 75% of their target) for supervisor intervention.
- Backfill the two Billing roles, cross-train Order Management agents (highest SLA compliance) on Billing, and review the 2025 billing/pricing change that drove the extra tickets.
- Map the refund workflow end-to-end, set a joint SLA between Returns support and the Refund Approval process owner, and give agents refund-status visibility.

Full detail: [business_insights.md](business_insights.md) · [recommendations.md](recommendations.md) · [customer_support_report.md](customer_support_report.md) · [operations_report.md](operations_report.md)

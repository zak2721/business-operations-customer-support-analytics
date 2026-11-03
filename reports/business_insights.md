# Business Insights

> **Data notice:** all figures are computed from a synthetic dataset generated for this portfolio project (seeded, reproducible). They demonstrate the analytical method and are not real company results.

_Generated 2026-10-30 by `src/analytics/reports.py`._

25 insights. **Finding** and **Evidence** are computed from data; **Hypothesis**, **Action** and **Expected outcome** are analyst judgement and must be validated before acting.

| # | Area | Insight | Priority |
|---:|---|---|---|
| 1 | Customer Support | [Asynchronous channels respond in hours, real-time channels in minutes](#1-asynchronous-channels-respond-in-hours-real-time-channels-in-minutes) | High |
| 2 | Customer Experience | [Satisfaction declines steadily as first response time grows](#2-satisfaction-declines-steadily-as-first-response-time-grows) | High |
| 3 | Customer Experience | [An SLA breach is the strongest measured driver of an unhappy customer](#3-an-sla-breach-is-the-strongest-measured-driver-of-an-unhappy-customer) | High |
| 4 | SLA & Service Quality | [Billing & Accounts SLA compliance collapsed in 2025](#4-billing--accounts-sla-compliance-collapsed-in-2025) | High |
| 5 | Cost | [Billing's outsourcing spend more than doubled without restoring service levels](#5-billings-outsourcing-spend-more-than-doubled-without-restoring-service-levels) | Medium |
| 6 | SLA & Service Quality | [Returns & Refunds has the weakest service performance of any department](#6-returns--refunds-has-the-weakest-service-performance-of-any-department) | High |
| 7 | Agent Performance | [Junior agents breach SLA and get reopened far more often](#7-junior-agents-breach-sla-and-get-reopened-far-more-often) | High |
| 8 | Customer Experience | [First-contact resolution lifts satisfaction by almost a full point](#8-first-contact-resolution-lifts-satisfaction-by-almost-a-full-point) | Medium |
| 9 | SLA & Service Quality | [Critical tickets have the lowest SLA compliance](#9-critical-tickets-have-the-lowest-sla-compliance) | High |
| 10 | SLA & Service Quality | [Most of the open backlog is stale rather than new](#10-most-of-the-open-backlog-is-stale-rather-than-new) | Medium |
| 11 | Customer Support | [November-December peaks overwhelm capacity](#11-november-december-peaks-overwhelm-capacity) | Medium |
| 12 | Agent Performance | [Agent-months with the heaviest workload resolve tickets more slowly](#12-agent-months-with-the-heaviest-workload-resolve-tickets-more-slowly) | Medium |
| 13 | Customer Experience | [Repeat contacts are common and concentrated in a small set of customers](#13-repeat-contacts-are-common-and-concentrated-in-a-small-set-of-customers) | Medium |
| 14 | Customer Experience | [Complaints are escalated most and satisfy least](#14-complaints-are-escalated-most-and-satisfy-least) | Medium |
| 15 | Customer Support | [Weekend tickets wait longer and score lower](#15-weekend-tickets-wait-longer-and-score-lower) | Low |
| 16 | Business Operations | [Refund Approval is the most failure-prone process and is getting worse](#16-refund-approval-is-the-most-failure-prone-process-and-is-getting-worse) | High |
| 17 | Business Operations | [Payment Reconciliation failures jumped after April 2025 and its unit cost is rising fastest](#17-payment-reconciliation-failures-jumped-after-april-2025-and-its-unit-cost-is-rising-fastest) | High |
| 18 | Business Operations | [Shipment Dispatch slows down sharply in peak season](#18-shipment-dispatch-slows-down-sharply-in-peak-season) | Medium |
| 19 | Cost | [Operational cost growth is mostly volume-driven, but unit costs are also rising](#19-operational-cost-growth-is-mostly-volume-driven-but-unit-costs-are-also-rising) | Medium |
| 20 | Cost | [Every department exceeded its annual budget in 2025](#20-every-department-exceeded-its-annual-budget-in-2025) | Medium |
| 21 | Cost | [Fully loaded cost per resolved ticket is broadly flat](#21-fully-loaded-cost-per-resolved-ticket-is-broadly-flat) | Low |
| 22 | Customer Experience | [High-value Enterprise customers receive the same service as consumers](#22-high-value-enterprise-customers-receive-the-same-service-as-consumers) | Medium |
| 23 | Agent Performance | [Agent outcomes vary widely, and SLA performance tracks satisfaction](#23-agent-outcomes-vary-widely-and-sla-performance-tracks-satisfaction) | Medium |
| 24 | Customer Experience | [Churned customers had only slightly worse support experiences](#24-churned-customers-had-only-slightly-worse-support-experiences) | Low |
| 25 | Predictive Analytics | [SLA-breach risk can be estimated at ticket creation](#25-sla-breach-risk-can-be-estimated-at-ticket-creation) | Medium |

## 1. Asynchronous channels respond in hours, real-time channels in minutes

**Area:** Customer Support · **Priority:** High

- **Finding (observed):** Average first response time is 13.47 h on Web Portal, 10.29 h on Email and 7.53 h on Social Media, versus 5 min on Phone and 8 min on Live Chat. SLA compliance follows the same split: 58.5-65.3% for asynchronous channels vs 84.3-86.0% for real-time.
- **Evidence:** KPI by channel (avg FRT, SLA compliance); SLA-breach logistic regression odds ratios vs Phone: Email 4.6x, Live Chat 1.2x, Social Media 4.2x, Web Portal 6.1x
- **Business impact:** Email and Web Portal carry 46.1% of all tickets, so their delays dominate the overall SLA and CSAT picture.
- **Root-cause hypothesis (to validate):** Asynchronous queues are worked in batches and are not staffed out of hours; tickets created in the evening or at weekends wait for the next shift.
- **Recommended action:** Introduce an auto-acknowledgement + triage rule for Email/Web Portal, set a 4-hour first-response target for those queues, and route simple categories (Account Access, Order Status, Product Inquiry) to live chat or self-service.
- **Expected measurable outcome:** Average FRT on Email/Web Portal falls below the 8 h Medium-priority FRT target; asynchronous SLA compliance converges toward the real-time level.
- **KPI to monitor:** Avg First Response Time by channel; SLA Compliance Rate by channel

## 2. Satisfaction declines steadily as first response time grows

**Area:** Customer Experience · **Priority:** High

- **Finding (observed):** Average CSAT is 4.14 when the first response arrives within 15 minutes, 3.50 at 4-8 hours and 2.95 after 24 hours (satisfied share 79.9% -> 29.0%).
- **Evidence:** Spearman rho = -0.372 (n = 12264); OLS coefficient on log(1+FRT) = -0.1608 CSAT points, holding SLA outcome, reopen, escalation, channel and category constant.
- **Business impact:** Response speed is the most controllable lever on customer experience; every additional delay band costs satisfaction.
- **Root-cause hypothesis (to validate):** Customers interpret a slow first reply as lack of ownership, independent of the eventual resolution.
- **Recommended action:** Publish FRT targets per priority (Critical 1 h, High 4 h, Medium 8 h, Low 24 h) on the team dashboard and alert supervisors when a ticket approaches its FRT target.
- **Expected measurable outcome:** Share of tickets with first response under 1 hour rises quarter over quarter; average CSAT of async channels rises.
- **KPI to monitor:** FRT compliance %, Avg CSAT by FRT band

## 3. An SLA breach is the strongest measured driver of an unhappy customer

**Area:** Customer Experience · **Priority:** High

- **Finding (observed):** 84.3% of customers whose ticket was resolved within SLA were satisfied (CSAT 4-5), versus 17.9% when the SLA was breached (avg CSAT 4.19 vs 2.79).
- **Evidence:** Mann-Whitney p < 0.001, rank-biserial effect 0.767; OLS coefficient for breach = -1.0254 points (95% CI -1.0574 to -0.9933); model R^2 = 0.5563.
- **Business impact:** With an overall breach rate of 27.1%, roughly one resolved ticket in four is a likely detractor.
- **Root-cause hypothesis (to validate):** Customers judge the experience primarily on whether the promised timeframe was kept.
- **Recommended action:** Make SLA compliance the primary team KPI and add an 'SLA at risk' queue (tickets at 75% of their target) for supervisor intervention.
- **Expected measurable outcome:** SLA breach rate falls; the satisfied share of resolved tickets rises in step.
- **KPI to monitor:** SLA Breach Rate; Customer Satisfaction Rate

## 4. Billing & Accounts SLA compliance collapsed in 2025

**Area:** SLA & Service Quality · **Priority:** High

- **Finding (observed):** Billing SLA compliance fell from 82.86% (2024) to 60.08% (2025), a 22.78-point drop. Billing ticket volume rose from 1,479 to 2,138 (+44.6%) while assignments per active Billing agent rose from 15.1 to 24.9 per month. 2 Billing agents are recorded as terminated.
- **Evidence:** Two-proportion z-test z = -14.389, p < 0.001; resolution time Mann-Whitney p < 0.001 (median 19.389 h -> 32.851 h).
- **Business impact:** Billing is the second-largest ticket category; its breaches directly affect revenue-related customer trust.
- **Root-cause hypothesis (to validate):** A demand increase from April 2025 (Billing & Payment share of tickets jumps) coincided with experienced-agent attrition, lowering capacity per ticket.
- **Recommended action:** Backfill the two Billing roles, cross-train Order Management agents (highest SLA compliance) on Billing, and review the 2025 billing/pricing change that drove the extra tickets.
- **Expected measurable outcome:** Billing SLA compliance returns toward its 2023-2024 level (>80%); tickets per Billing agent return to the 2024 level.
- **KPI to monitor:** SLA Compliance (Billing), Tickets per Agent (Billing), Billing ticket volume

## 5. Billing's outsourcing spend more than doubled without restoring service levels

**Area:** Cost · **Priority:** Medium

- **Finding (observed):** Billing outsourcing cost rose from $53,063 (2023) to $117,242 (2025), +120.9%, the largest category-level increase in the company, while Billing SLA compliance fell to 60.08%.
- **Evidence:** Business costs by department x category, 2023 vs 2025 (rca_business_cost_growth.csv).
- **Business impact:** Spend increased in the same period that service quality fell, so cost per compliant ticket rose sharply.
- **Root-cause hypothesis (to validate):** Outsourced capacity was added reactively and handles low-complexity work, or ramps up slowly; it did not offset the loss of experienced in-house agents.
- **Recommended action:** Attach SLA and FCR targets to the outsourcing contract and report outsourced vs in-house ticket outcomes separately.
- **Expected measurable outcome:** Outsourcing cost is tied to measurable throughput; cost per SLA-compliant Billing ticket falls.
- **KPI to monitor:** Departmental Cost (Billing, Outsourcing); Cost per Resolved Ticket

## 6. Returns & Refunds has the weakest service performance of any department

**Area:** SLA & Service Quality · **Priority:** High

- **Finding (observed):** Returns & Refunds resolves only 50.0% of tickets within SLA (company 72.9%), has the longest average resolution time (59.8 h) and the highest reopen rate (14.6%).
- **Evidence:** KPI by department; root-cause lift for SLA breach = 1.85x baseline.
- **Business impact:** Refund delays are high-emotion contacts and generate repeat contacts and reopenings.
- **Root-cause hypothesis (to validate):** Refund resolution depends on the Returns Inspection and Refund Approval processes, both of which show elevated failure rates and processing times (see operations insights).
- **Recommended action:** Map the refund workflow end-to-end, set a joint SLA between Returns support and the Refund Approval process owner, and give agents refund-status visibility.
- **Expected measurable outcome:** Returns & Refunds SLA compliance and reopen rate move toward company averages.
- **KPI to monitor:** SLA Compliance (Returns & Refunds); Reopen Rate; Refund Approval failure rate

## 7. Junior agents breach SLA and get reopened far more often

**Area:** Agent Performance · **Priority:** High

- **Finding (observed):** Junior agents meet SLA on 53.2% of tickets vs 80.4% for Leads; their reopen rate is 16.6% vs 5.7% and average CSAT 3.41 vs 3.88.
- **Evidence:** Mann-Whitney on resolution hours (Junior vs Senior/Lead) p < 0.001; logistic regression odds ratio for SLA breach, Junior vs Lead = 5.2x after controlling for priority, channel, category and season.
- **Business impact:** Junior agents handled 2,748 tickets; their excess breaches and reopens consume senior capacity later.
- **Root-cause hypothesis (to validate):** Juniors receive the same ticket mix as experienced agents without a structured ramp-up or knowledge base.
- **Recommended action:** Route Critical/High and complex categories away from agents with < 2 years tenure, pair juniors with a senior buddy, and review reopened tickets weekly as coaching material.
- **Expected measurable outcome:** The SLA and reopen gap between Junior and Mid-Level agents narrows each quarter.
- **KPI to monitor:** SLA Compliance by experience level; Reopen Rate by experience level

## 8. First-contact resolution lifts satisfaction by almost a full point

**Area:** Customer Experience · **Priority:** Medium

- **Finding (observed):** Tickets resolved on first contact average CSAT 4.471 vs 3.573 otherwise. FCR is 33.0% on Phone and 29.5% on Live Chat but only 13.6% on Email and 11.4% on Web Portal (overall 21.5%).
- **Evidence:** Mann-Whitney p < 0.001; OLS coefficient for FCR = +0.2555 after controls.
- **Business impact:** Each ticket solved at first contact avoids follow-up handling time and raises satisfaction.
- **Root-cause hypothesis (to validate):** Written channels lack the information needed to resolve on the first reply (account, order or error details).
- **Recommended action:** Add structured intake forms (order ID, error code, account) to Email/Web Portal and give agents macros for the top subcategories.
- **Expected measurable outcome:** FCR on Email/Web Portal rises; average handling touches per ticket fall.
- **KPI to monitor:** First Contact Resolution Rate by channel

## 9. Critical tickets have the lowest SLA compliance

**Area:** SLA & Service Quality · **Priority:** High

- **Finding (observed):** Only 54.7% of Critical tickets are resolved within their 8-hour SLA, versus 78.3% of Low-priority tickets within 72 hours. Critical tickets are escalated 18.9% of the time.
- **Evidence:** Chi-square priority x SLA breach p < 0.001 (Cramer's V 0.133); odds ratio Critical vs Low = 4.2x.
- **Business impact:** 1,655 Critical tickets represent the highest-impact customer incidents.
- **Root-cause hypothesis (to validate):** The 8-hour target is tight relative to escalation hand-offs; Critical tickets are not ring-fenced from the general queue.
- **Recommended action:** Create a dedicated Critical-incident rota with Senior/Lead agents, and auto-page Tier 2 at creation rather than after first triage.
- **Expected measurable outcome:** Critical SLA compliance rises; escalation-to-resolution time for Critical tickets falls.
- **KPI to monitor:** SLA Compliance (Critical); Avg Resolution Time by Priority

## 10. Most of the open backlog is stale rather than new

**Area:** SLA & Service Quality · **Priority:** Medium

- **Finding (observed):** Of 257 open tickets at 31 Dec 2025, 155 (60.3%) are older than 30 days and 110 are older than 60 days. 44 have never received a first response. The month-end backlog grew from 55 (Aug 2025) to 257 (Dec 2025).
- **Evidence:** Ticket aging distribution (open = Open, In Progress, Pending).
- **Business impact:** Aged tickets are almost certain SLA breaches and likely churn risks; they also distort backlog-based staffing.
- **Root-cause hypothesis (to validate):** Pending tickets waiting on customer replies are not auto-closed and in-progress tickets lack ownership reviews.
- **Recommended action:** Run a backlog scrub, introduce auto-close after a defined no-reply period for Pending tickets, and add a weekly aged-ticket review by team leads.
- **Expected measurable outcome:** Tickets older than 30 days fall to a small fraction of the backlog; 'Open with no first response' approaches zero.
- **KPI to monitor:** Aging Ticket Backlog (>7, >30 days); Ticket Backlog

## 11. November-December peaks overwhelm capacity

**Area:** Customer Support · **Priority:** Medium

- **Finding (observed):** Average monthly volume is 854 tickets in Nov-Dec vs 602 in Jun-Aug. SLA compliance in Nov-Dec is 62.7% vs 75.6% for the rest of the year.
- **Evidence:** Odds ratio for Q4 in the SLA-breach logistic regression = 2.34x.
- **Business impact:** The peak coincides with the highest-revenue period; service failures then have outsized commercial cost.
- **Root-cause hypothesis (to validate):** Staffing is flat across the year while demand is seasonal.
- **Recommended action:** Use the monthly volume profile to plan seasonal temporary staff and freeze leave in Nov-Dec; pre-publish holiday delivery FAQs.
- **Expected measurable outcome:** The Nov-Dec SLA gap versus the rest of the year narrows.
- **KPI to monitor:** Monthly SLA Compliance; Tickets per Agent (monthly)

## 12. Agent-months with the heaviest workload resolve tickets more slowly

**Area:** Agent Performance · **Priority:** Medium

- **Finding (observed):** In the top workload quintile (avg 23.1 tickets assigned/month) average resolution time is 37.3 h and SLA compliance 69.6%, vs 32.3 h and 75.2% in the other quintiles.
- **Evidence:** Spearman rho workload vs resolution time = 0.14 (weak but significant, n = 1984 agent-months).
- **Business impact:** The effect appears only at the high end, which points to a capacity threshold rather than a gradual slowdown.
- **Root-cause hypothesis (to validate):** Above roughly 17 new tickets per agent per month, agents switch context too often to keep up.
- **Recommended action:** Set a soft cap on monthly assignments per agent and rebalance via skills-based routing when an agent exceeds it.
- **Expected measurable outcome:** Fewer agent-months fall into the top workload band; resolution time variance across agents narrows.
- **KPI to monitor:** Tickets per Agent; Agent workload distribution

## 13. Repeat contacts are common and concentrated in a small set of customers

**Area:** Customer Experience · **Priority:** Medium

- **Finding (observed):** 16.0% of tickets arrive within 7 days of the same customer's previous ticket. The top 10% of contacting customers generate 42.4% of all tickets.
- **Evidence:** 7-day repeat-contact flag; ticket concentration by customer.
- **Business impact:** Repeat contacts inflate volume without new demand and signal unresolved root problems for key accounts.
- **Root-cause hypothesis (to validate):** High-usage (mostly Enterprise and Mid-Market) customers hit the same issues repeatedly; fixes are not followed up proactively.
- **Recommended action:** Assign named account contacts to the top-volume customers and run quarterly root-cause reviews of their ticket history.
- **Expected measurable outcome:** 7-day repeat contact rate declines; ticket volume from top-decile customers grows more slowly than their usage.
- **KPI to monitor:** Customer Repeat Contact Rate; tickets per customer (top decile)

## 14. Complaints are escalated most and satisfy least

**Area:** Customer Experience · **Priority:** Medium

- **Finding (observed):** Complaint tickets are escalated 23.5% of the time (company 10.2%) and have the lowest average CSAT (3.26) and FCR (6.8%).
- **Evidence:** KPI by category; root-cause lift for escalation.
- **Business impact:** Complaints are the strongest churn signal and consume senior time through escalations.
- **Root-cause hypothesis (to validate):** Front-line agents lack authority to offer remedies (credits, exceptions), so complaints must be escalated.
- **Recommended action:** Give Senior agents a defined goodwill-credit authority and a complaint-handling playbook so most complaints close without escalation.
- **Expected measurable outcome:** Complaint escalation rate and resolution time fall; complaint CSAT rises.
- **KPI to monitor:** Escalation Rate (Complaint); Avg CSAT (Complaint)

## 15. Weekend tickets wait longer and score lower

**Area:** Customer Support · **Priority:** Low

- **Finding (observed):** Tickets created at weekends wait 13.48 h on average for a first response vs 4.26 h on weekdays; their average CSAT is 3.54 vs 3.79.
- **Evidence:** Low-CSAT root-cause lift for Saturday = 1.74x.
- **Business impact:** Weekend volume is lower, so a small coverage change could remove most of the gap.
- **Root-cause hypothesis (to validate):** Asynchronous queues are not monitored at weekends.
- **Recommended action:** Add a light weekend rota for Email/Web Portal triage (first response only).
- **Expected measurable outcome:** Weekend FRT approaches weekday FRT.
- **KPI to monitor:** Avg First Response Time (weekend vs weekday)

## 16. Refund Approval is the most failure-prone process and is getting worse

**Area:** Business Operations · **Priority:** High

- **Finding (observed):** Refund Approval's failure rate rose from 7.06% (2023) to 10.23% (2025), about 5.1x the company average; 89.4% of its operating days were 'Degraded' or 'Critical'.
- **Evidence:** Operations failure rate by process and year; operational bottleneck score.
- **Business impact:** Failed refund approvals feed directly into Returns & Refunds tickets, reopenings and SLA breaches.
- **Root-cause hypothesis (to validate):** Manual approval steps and inconsistent policy rules cause rejections that later need rework.
- **Recommended action:** Audit the top rejection reasons, automate rule-based approvals under a value threshold, and add a daily failure-rate alert.
- **Expected measurable outcome:** Refund Approval failure rate trends back toward its 2023 level; Returns & Refunds reopen rate falls.
- **KPI to monitor:** Operational Failure Rate (Refund Approval); Reopen Rate (Returns & Refunds)

## 17. Payment Reconciliation failures jumped after April 2025 and its unit cost is rising fastest

**Area:** Business Operations · **Priority:** High

- **Finding (observed):** Failure rate was 3.18% before April 2025 and 5.90% after. Its cost per transaction grew 12.0% between 2023 and 2025, the highest of any process.
- **Evidence:** Operations by process (pre/post April 2025); price-volume cost decomposition.
- **Business impact:** The timing matches the jump in Billing tickets, suggesting the same upstream change affects both operations and support.
- **Root-cause hypothesis (to validate):** The April 2025 pricing/billing change introduced reconciliation mismatches that surface as failed transactions and customer billing tickets.
- **Recommended action:** Run a joint incident review between Billing operations and Billing support on the April 2025 change; fix mapping rules for new price plans.
- **Expected measurable outcome:** Payment Reconciliation failure rate returns to its pre-April level; Billing ticket share declines.
- **KPI to monitor:** Operational Failure Rate (Payment Reconciliation); Billing & Payment ticket volume

## 18. Shipment Dispatch slows down sharply in peak season

**Area:** Business Operations · **Priority:** Medium

- **Finding (observed):** Shipment Dispatch takes 6.29 min per transaction in Nov-Dec vs 4.04 min the rest of the year (+55.6%). It is also the largest single operating cost line ($2.48M over 3 years).
- **Evidence:** Volume-weighted processing time by process and month.
- **Business impact:** Slower dispatch in peak season is consistent with the Nov-Dec rise in Delivery Problem tickets and SLA breaches.
- **Root-cause hypothesis (to validate):** Warehouse dispatch capacity is fixed while order volume peaks.
- **Recommended action:** Pre-book carrier capacity and temporary warehouse staff for Nov-Dec; add dispatch-delay proactive notifications to customers.
- **Expected measurable outcome:** Peak-season dispatch time approaches the off-peak level; Delivery Problem tickets in Nov-Dec fall.
- **KPI to monitor:** Avg Processing Time (Shipment Dispatch); Delivery Problem ticket volume

## 19. Operational cost growth is mostly volume-driven, but unit costs are also rising

**Area:** Cost · **Priority:** Medium

- **Finding (observed):** Transaction-processing cost grew by $0.81M between 2023 and 2025. $0.65M (80.1%) is explained by higher volume and $0.16M by higher cost per transaction.
- **Evidence:** Price-volume decomposition per process; Pearson r between daily volume and cost = 0.99 (Spearman).
- **Business impact:** Volume growth is a business success; the unit-cost component is the controllable inefficiency.
- **Root-cause hypothesis (to validate):** Rework from failed transactions and vendor price increases drive unit cost.
- **Recommended action:** Track cost per transaction by process monthly, and prioritise automation where unit cost is rising (Payment Reconciliation, Shipment Dispatch, Returns Inspection).
- **Expected measurable outcome:** Cost per transaction stabilises or falls while volume grows.
- **KPI to monitor:** Average Cost per Transaction; Operational Efficiency Rate

## 20. Every department exceeded its annual budget in 2025

**Area:** Cost · **Priority:** Medium

- **Finding (observed):** 2025 spend as a share of budget ranged from 108.8% to 121.8% (highest: Billing & Accounts). Total departmental cost was $3.89M against $3.49M budgeted.
- **Evidence:** Business costs vs department operational_budget, by year.
- **Business impact:** Budgets have not been re-baselined for growth, so overruns are structural rather than one-off.
- **Root-cause hypothesis (to validate):** Budgets are flat year-on-year while volume and wage costs grow.
- **Recommended action:** Re-baseline budgets on a cost-per-ticket and cost-per-transaction driver model, and review Billing's overrun separately.
- **Expected measurable outcome:** Budget utilisation returns close to 100% with explainable variances.
- **KPI to monitor:** Departmental Cost vs Budget; Cost per Resolved Ticket

## 21. Fully loaded cost per resolved ticket is broadly flat

**Area:** Cost · **Priority:** Low

- **Finding (observed):** Cost per resolved ticket (departmental cost / resolved tickets) was $504 in 2023, $468 in 2024, $471 in 2025.
- **Evidence:** Business costs and resolved tickets by year.
- **Business impact:** The change from 2023 to 2025 is -6.5%: volume growth is translating almost one-for-one into cost growth, with little scale benefit.
- **Root-cause hypothesis (to validate):** Headcount and overheads grow roughly in line with ticket volume.
- **Recommended action:** Use FCR, reopen and repeat-contact reductions (insights 8, 13, 16) as the main cost-efficiency levers.
- **Expected measurable outcome:** Cost per resolved ticket declines while SLA compliance holds.
- **KPI to monitor:** Cost per Resolved Ticket

## 22. High-value Enterprise customers receive the same service as consumers

**Area:** Customer Experience · **Priority:** Medium

- **Finding (observed):** SLA compliance is 72.6-73.4% across all four segments, even though median CLV is $42,570 for Enterprise vs $637 for Consumer customers.
- **Evidence:** Chi-square segment x SLA breach p = 0.80 (no significant difference).
- **Business impact:** Service is consistent, but there is no protection for the accounts with the most revenue at stake.
- **Root-cause hypothesis (to validate):** Routing does not use customer segment or CLV.
- **Recommended action:** Introduce segment-aware routing or a premium SLA tier for Enterprise accounts.
- **Expected measurable outcome:** Enterprise SLA compliance and CSAT rise above the company average.
- **KPI to monitor:** SLA Compliance by segment; CSAT by segment

## 23. Agent outcomes vary widely, and SLA performance tracks satisfaction

**Area:** Agent Performance · **Priority:** Medium

- **Finding (observed):** Among agents with at least 100 tickets, SLA compliance ranges from 32.5% to 95.7% and average CSAT from 3.21 to 4.29. Agent-level SLA and CSAT correlate (Spearman rho 0.71).
- **Evidence:** Agent scorecard (tickets, SLA, CSAT, reopen) built from ticket-level data.
- **Business impact:** The spread means peer coaching from top performers is available inside the team.
- **Root-cause hypothesis (to validate):** Differences reflect experience, category mix and individual practice.
- **Recommended action:** Run monthly calibration sessions where top-quartile agents share handling approaches; compare agents within the same department and category mix.
- **Expected measurable outcome:** The bottom-quartile agent SLA compliance rises; the spread narrows.
- **KPI to monitor:** SLA Compliance by agent; Avg CSAT by agent

## 24. Churned customers had only slightly worse support experiences

**Area:** Customer Experience · **Priority:** Low

- **Finding (observed):** Average CSAT on tickets from customers now marked Churned is 3.66 vs 3.76 for Active customers; SLA compliance 71.1% vs 73.0%.
- **Evidence:** Ticket KPIs grouped by current customer status.
- **Business impact:** Support experience is at most one factor in churn here; the difference is small.
- **Root-cause hypothesis (to validate):** Churn is mostly driven by factors outside support (price, product fit); data on those is not in scope.
- **Recommended action:** Do not use support KPIs alone as a churn early-warning signal; combine with product usage and billing data in a future churn model.
- **Expected measurable outcome:** A churn model with richer features is scoped before any retention spend is targeted.
- **KPI to monitor:** Churn rate; CSAT of churned vs active

## 25. SLA-breach risk can be estimated at ticket creation

**Area:** Predictive Analytics · **Priority:** Medium

- **Finding (observed):** A Gradient Boosting model using only creation-time attributes reached ROC-AUC 0.7987 on 2025 tickets (trained on 2023-2024). Tickets in the top predicted-risk decile breached SLA 75.27% of the time vs 0.73% in the bottom decile.
- **Evidence:** Time-based hold-out; precision 0.5569, recall 0.6094, F1 0.582 at threshold 0.54. Most important features: support_channel, ticket_category, experience_level, ticket_subcategory.
- **Business impact:** A risk score lets supervisors act before a breach instead of reporting it afterwards.
- **Root-cause hypothesis (to validate):** The same drivers found in root-cause analysis (channel, category, agent experience, season) make breach risk predictable.
- **Recommended action:** Pilot a 'high breach risk' tag in the ticketing system for the top decile and measure its effect with an A/B comparison before rollout.
- **Expected measurable outcome:** Breach rate among tagged tickets falls relative to an untagged control group.
- **KPI to monitor:** SLA Breach Rate (tagged vs control)

# KPI Definitions

One definition per KPI, implemented identically in three places:

| Layer | Implementation |
|---|---|
| Python | `src/kpi/kpis.py` (`compute_all_kpis`, `kpi_by`, `ops_by`) |
| SQL | `sql/09_reporting_views/01_reporting_views.sql` (`v_ticket_metrics`, `v_kpi_summary`, ...) |
| DAX | `powerbi/dax_measures.dax` |

`tests/test_sql.py` asserts that the SQL view and the Python engine return the same values; `powerbi/validation/expected_kpi_values.csv` lets you check the DAX in Power BI against the same numbers.

## Ticket populations (denominators)

Every rate below names its population explicitly. The populations are flags on each ticket, built once in `src/feature_engineering/features.py`.

| Population | Rule | Count (all data) |
|---|---|---:|
| All tickets | every non-duplicate ticket | 24,000 |
| Actionable | all tickets except **Cancelled** | 23,493 |
| Resolved | status **Closed** or **Resolved** | 23,236 |
| **SLA-eligible** | resolved **and** has a valid resolution timestamp | 23,211 |
| Unresolved (backlog) | status **Open**, **In Progress** or **Pending** | 257 |
| Responded | has a first-response timestamp | — |
| Valid survey | survey with a CSAT score on the 1-5 scale | — |

### How special statuses are treated

| Status / condition | Volume KPIs | Resolution & SLA & FCR | Resolution rate | Backlog / aging |
|---|---|---|---|---|
| Closed, Resolved | counted | **included** | numerator & denominator | — |
| Open, In Progress, Pending | counted | **excluded** (no resolution yet) | denominator only | **included** |
| Cancelled | counted in Total | excluded | excluded | excluded |
| Reopened (any status) | counted once (not once per reopen) | included if now resolved; final resolution time used | as per status | as per status |
| Resolved with invalid timestamp (25 tickets) | counted | excluded (time unknown) | counted as resolved | — |

Unresolved tickets are never put into the SLA compliance rate. Their SLA risk is measured separately by **Open Tickets Past SLA** / **aging backlog** (tickets whose age already exceeds their SLA target).

## Customer support KPIs

| # | KPI | Formula | Population / notes |
|---|---|---|---|
| 1 | Total Tickets | `COUNT(tickets)` | all |
| 2 | Open Tickets | `COUNT(status ∈ {Open, In Progress, Pending})` | state at snapshot 31-Dec-2025 |
| 3 | Closed Tickets | `COUNT(status ∈ {Closed, Resolved})` | "Resolved Tickets" is the same number |
| 4 | Pending Tickets | `COUNT(status = Pending)` | waiting on customer |
| 5 | Escalated Tickets | `SUM(escalation_flag)` | |
| 6 | Reopened Tickets | `COUNT(reopened_count > 0)` | a ticket reopened twice counts once |
| 7 | Avg First Response Time | `AVG(first_response − created)` in hours | responded tickets only |
| 8 | Median First Response Time | `MEDIAN(first_response − created)` | robust to the long async tail (mean 5.8 h vs median 1.1 h) |
| 9 | Avg Resolution Time | `AVG(resolved − created)` in hours | **SLA-eligible** tickets only |
| 10 | First Contact Resolution Rate | `COUNT(eligible ∧ resolution_type = 'First Contact Resolution' ∧ reopened_count = 0 ∧ escalation_flag = 0) / COUNT(eligible) × 100` | SLA-eligible |
| 11 | Ticket Resolution Rate | `COUNT(resolved) / COUNT(actionable) × 100` | completion, not speed |
| 12 | SLA Compliance Rate | `COUNT(eligible ∧ resolution_hours ≤ sla_target_hours) / COUNT(eligible) × 100` | SLA-eligible |
| 13 | SLA Breach Rate | `COUNT(eligible ∧ resolution_hours > sla_target_hours) / COUNT(eligible) × 100` | = 100 − #12 |
| 14 | Ticket Backlog | = Open Tickets | plus **Aging Backlog** = open and older than 7 days |
| 15 | Avg Customer Satisfaction | `AVG(satisfaction_score)` | valid surveys; missing scores never imputed or treated as 0 |
| 16 | Customer Satisfaction Rate | `COUNT(score ≥ 4) / COUNT(valid score) × 100` | valid surveys |
| 17 | Tickets per Agent | `COUNT(tickets with known agent) / COUNT(DISTINCT agent)` | |
| 18 | Agent Productivity Rate | `COUNT(resolved, known agent) / COUNT(actionable, known agent) × 100` | |

**SLA targets (resolution, from creation):** Critical 8 h · High 24 h · Medium 48 h · Low 72 h.
**First-response targets:** Critical 1 h · High 4 h · Medium 8 h · Low 24 h.

### Three rates that are often confused

| Rate | Question it answers | Numerator | Denominator |
|---|---|---|---|
| **Ticket resolution rate** | Did we finish the work? | resolved | actionable (non-cancelled) |
| **SLA compliance rate** | Did we finish it *on time*? | eligible resolved within target | eligible resolved |
| **First contact resolution** | Did we finish it *in one interaction*, without rework? | eligible resolved on first contact, never reopened or escalated | eligible resolved |

A ticket can count toward resolution rate but breach SLA, or meet SLA without being FCR.

## Business operations KPIs

| # | KPI | Formula | Notes |
|---|---|---|---|
| 19 | Total Transactions | `SUM(total_transactions)` | |
| 20 | Successful Transactions | `SUM(successful_transactions)` | |
| 21 | Failed Transactions | `SUM(failed_transactions)` | successful + failed = total (enforced) |
| 22 | Operational Success Rate | `SUM(successful) / SUM(total) × 100` | ratio of sums, **not** average of daily rates |
| 23 | Operational Failure Rate | `SUM(failed) / SUM(total) × 100` | |
| 24 | Average Processing Time | `SUM(processing_time_minutes × total_transactions) / SUM(total_transactions)` | transaction-weighted |
| 25 | Total Operational Cost | `SUM(operational_cost)` | variable transaction-processing cost |
| 26 | Average Cost per Transaction | `SUM(operational_cost) / SUM(total_transactions)` | |
| 27 | Cost per Resolved Ticket | `SUM(business_costs.total_cost) / COUNT(resolved tickets)` | fully loaded departmental cost, same period |
| 28 | Departmental Cost | `SUM(total_cost)` by department | staffing & overhead (direct + indirect) |
| 29 | Operational Efficiency Rate | `SUM(successful) / SUM(operational_cost) × 1000` | successful transactions per $1,000 |
| 30 | Customer Repeat Contact Rate | `COUNT(ticket created ≤ 7 days after the same customer's previous ticket) / COUNT(tickets) × 100` | ticket-level; customer-level "repeat customer rate" also reported |

## Avoiding misleading numbers

* **No averages of percentages.** Every rate is recomputed from summed numerators and denominators at the level being shown.
* **Medians alongside means** for time metrics, which are heavily right-skewed.
* **Blank ≠ zero.** Missing CSAT, missing first response and unresolved resolution times are excluded, never zero-filled.
* **One survey per ticket** (enforced by cleaning and a `UNIQUE` constraint) so CSAT is not double counted.
* **Date semantics are explicit:** ticket KPIs by creation date (cohort); a resolved-date variant exists in DAX for throughput views; CSAT by survey date in Power BI.

## Headline values (all data, seed 42)

Taken from `data/reports/kpi_summary.json` (identical to SQL `support.v_kpi_summary`):

| KPI | Value | KPI | Value |
|---|---:|---|---:|
| Total Tickets | 24,000 | Operational Success Rate | 98.00% |
| Open Tickets | 257 | Operational Failure Rate | 2.00% |
| Avg First Response | 5.76 h | Avg Processing Time | 2.77 min |
| Avg Resolution | 34.46 h | Total Operational Cost | $11.94M |
| SLA Compliance | 72.91% | Avg Cost per Transaction | $0.797 |
| FCR | 21.49% | Cost per Resolved Ticket | $479.98 |
| Avg CSAT | 3.75 / 5 | Repeat Contact Rate | 15.97% |
| CSAT Rate | 63.36% | Escalation Rate | 10.23% |

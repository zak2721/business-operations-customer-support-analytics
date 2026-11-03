# SQL Documentation

PostgreSQL 16 analytical layer. **Every query below was executed against the loaded database** by `python -m src.database.run_sql`; the previews are the first rows of the real output and the full results are saved in `data/reports/sql_results/`.

* Analytical queries: **46**  ·  data-quality checks: **8**  ·  reporting views: **11**
* Schema: `sql/01_database_setup/` (3NF tables, PK/FK, CHECK constraints for business rules, indexes)
* Loading: `python -m src.database.load_postgres` (COPY from `data/processed/`, row counts verified)
* KPI definitions are identical to `src/kpi/kpis.py` and `powerbi/dax_measures.dax`; `tests/test_sql.py` asserts SQL = Python.

## How to run

```bash
cp .env.example .env            # set PGHOST / PGUSER / PGPASSWORD
python -m src.database.load_postgres   # creates DB + schema, loads data, builds indexes
python -m src.database.run_sql         # creates views, runs every query, regenerates this file
```

## Schema overview

| Table | Grain | Key constraints |
|---|---|---|
| departments | department | PK department_id, budget ≥ 0 |
| agents | agent | PK agent_id, FK department, experience/status domains |
| customers | customer | PK customer_id, segment/type/status domains, CLV ≥ 0 |
| calendar | day | PK date |
| support_tickets | ticket | PK, FKs, priority/status/channel domains, chronology checks, SLA target = f(priority) |
| customer_feedback | survey | PK, **UNIQUE ticket_id** (prevents CSAT double counting), CSAT 1-5, rating 1-10 |
| operations | process-day | PK, UNIQUE (date, process), success + failed = total, cost ≥ 0 |
| agent_performance | agent-month | PK, UNIQUE (agent, month), SLA % 0-100 |
| business_costs | dept-month-category | PK, UNIQUE, total = direct + indirect |

## Reporting views (`sql/09_reporting_views/01_reporting_views.sql`)

| View | Purpose |
|---|---|
| v_ticket_metrics | ticket grain + FRT/resolution hours, SLA/FCR/repeat flags, age, CSAT |
| v_kpi_summary | single-row headline KPIs |
| v_monthly_support_kpis | monthly volume, FRT, resolution, SLA, FCR, CSAT |
| v_department_sla | SLA by department and year |
| v_agent_scorecard | per-agent volume, productivity, SLA, reopen, CSAT |
| v_channel_performance | per-channel KPIs |
| v_backlog_aging | open tickets by age bucket |
| v_operations_monthly / v_process_performance | operations by month / process |
| v_cost_by_department_month | departmental cost vs monthly budget |
| v_customer_360 | customer-level support profile (no contact details) |

## SQL techniques covered

`AVG`, `AVG / PERCENTILE_CONT with FILTER`, `AVG() OVER (PARTITION BY)`, `AVG() OVER ROWS moving average`, `AVG() OVER ROWS window`, `CASE WHEN bucketing`, `CASE WHEN inside SUM (conditional aggregation)`, `CASE bucketing`, `CASE ordering`, `CASE segmentation matrix`, `COALESCE`, `COUNT`, `COUNT(DISTINCT)`, `CROSS JOIN to company-level totals`, `CTE`, `CUME_DIST`, `DATE_PART`, `DATE_TRUNC`, `DISTINCT inside aggregate`, `EXTRACT(ISODOW/HOUR)`, `EXTRACT(YEAR)`, `FILTERed weighted averages`, `FIRST_VALUE for index`, `GROUP BY`, `GROUP BY ... HAVING COUNT(*) > 1`, `GROUP BY ROLLUP`, `GROUP BY three dimensions`, `GROUP BY two dimensions`, `HAVING`, `HAVING on volume`, `HAVING-style filter on window result`, `INNER JOIN`, `INNER JOIN to view`, `IS NULL anti-join`, `JOIN`, `LAG`, `LAG for year-over-year growth`, `LAG over customer partition (in view)`, `LAG with offset 12`, `LEAD`, `LEAD to find next category`, `LEAD window function for gap detection`, `LEFT JOIN`, `LEFT JOIN (customers without tickets)`, `LEFT JOIN for unknown agents`, `NTILE`, `NTILE for value tiers`, `NULLIF for safe division`, `ORDER BY`, `ORDER BY ... LIMIT`, `PARTITION BY agent`, `PERCENT_RANK`, `RIGHT JOIN (keeps every agent)`, `SELECT`, `SUBSTRING on month key`, `SUM() OVER running total`, `UNION ALL`, `UNION of two aggregates`, `WHERE`, `aggregate functions`, `aggregation by month`, `aggregation of window output`, `conditional AVG with FILTER`, `conditional aggregation`, `conditional aggregation (pivot)`, `conditional aggregation pivot`, `correlated aggregation over a date spine`, `correlated subquery`, `date comparison`, `date filters`, `derived difference column`, `derived utilisation %`, `differences in percentage points`, `generate_series`, `growth calculation`, `multi-table JOIN`, `ordering by band`, `ratio`, `reporting view`, `scalar subqueries`, `share of total via window`, `subquery in FROM`, `two CTEs joined on department and year`, `view reuse`, `weighted average`, `window SUM() OVER () for share of total`, `window comparison to department average`, `window functions RANK / DENSE_RANK / ROW_NUMBER with PARTITION BY`

## Query catalogue

| ID | Title | Rows | File |
|---|---|---:|---|
| [DQ.01](#dq01) | Row counts per table | 9 | `sql/03_data_quality/data_quality_checks.sql` |
| [DQ.02](#dq02) | Orphan foreign keys (LEFT JOIN anti-join) | 3 | `sql/03_data_quality/data_quality_checks.sql` |
| [DQ.03](#dq03) | Ticket chronology and status consistency | 1 | `sql/03_data_quality/data_quality_checks.sql` |
| [DQ.04](#dq04) | Feedback consistency with its ticket | 1 | `sql/03_data_quality/data_quality_checks.sql` |
| [DQ.05](#dq05) | Duplicate business keys | 2 | `sql/03_data_quality/data_quality_checks.sql` |
| [DQ.06](#dq06) | Tickets created before customer registration or agent hire | 1 | `sql/03_data_quality/data_quality_checks.sql` |
| [DQ.07](#dq07) | Cleaning flags carried into the database | 1 | `sql/03_data_quality/data_quality_checks.sql` |
| [DQ.08](#dq08) | Calendar coverage | 1 | `sql/03_data_quality/data_quality_checks.sql` |
| [Q04.01](#q0401) | Customer base by segment | 4 | `sql/04_customer_analysis/customer_analysis.sql` |
| [Q04.02](#q0402) | Customers by region and country | 15 | `sql/04_customer_analysis/customer_analysis.sql` |
| [Q04.03](#q0403) | New customer registrations per year | 5 | `sql/04_customer_analysis/customer_analysis.sql` |
| [Q04.04](#q0404) | Distinct contacting customers per year | 3 | `sql/04_customer_analysis/customer_analysis.sql` |
| [Q04.05](#q0405) | Customer contact-frequency segmentation | 4 | `sql/04_customer_analysis/customer_analysis.sql` |
| [Q04.06](#q0406) | Top 15 customers by ticket volume (repeat contacts) | 15 | `sql/04_customer_analysis/customer_analysis.sql` |
| [Q04.07](#q0407) | Support experience by customer status | 3 | `sql/04_customer_analysis/customer_analysis.sql` |
| [Q04.08](#q0408) | Customers whose CSAT is below their segment average | 15 | `sql/04_customer_analysis/customer_analysis.sql` |
| [Q05.01](#q0501) | Ticket status distribution | 6 | `sql/05_customer_support_analysis/customer_support_analysis.sql` |
| [Q05.02](#q0502) | Ticket volume by category and subcategory | 43 | `sql/05_customer_support_analysis/customer_support_analysis.sql` |
| [Q05.03](#q0503) | Response and resolution by channel | 6 | `sql/05_customer_support_analysis/customer_support_analysis.sql` |
| [Q05.04](#q0504) | Resolution time by priority vs SLA target | 4 | `sql/05_customer_support_analysis/customer_support_analysis.sql` |
| [Q05.05](#q0505) | Ticket volume by weekday and hour band | 7 | `sql/05_customer_support_analysis/customer_support_analysis.sql` |
| [Q05.06](#q0506) | Escalations and reopenings by category | 8 | `sql/05_customer_support_analysis/customer_support_analysis.sql` |
| [Q05.07](#q0507) | First contact resolution by channel and category | 15 | `sql/05_customer_support_analysis/customer_support_analysis.sql` |
| [Q05.08](#q0508) | Open backlog by aging bucket | 6 | `sql/05_customer_support_analysis/customer_support_analysis.sql` |
| [Q05.09](#q0509) | Oldest open tickets (aging list) | 15 | `sql/05_customer_support_analysis/customer_support_analysis.sql` |
| [Q05.10](#q0510) | CSAT by first response time band | 6 | `sql/05_customer_support_analysis/customer_support_analysis.sql` |
| [Q05.11](#q0511) | CSAT by channel with SLA outcome | 5 | `sql/05_customer_support_analysis/customer_support_analysis.sql` |
| [Q05.12](#q0512) | Feedback themes | 6 | `sql/05_customer_support_analysis/customer_support_analysis.sql` |
| [Q06.01](#q0601) | Agent scorecard | 20 | `sql/06_agent_performance/agent_performance.sql` |
| [Q06.02](#q0602) | Agent ranking within department (RANK, DENSE_RANK, ROW_NUMBER) | 58 | `sql/06_agent_performance/agent_performance.sql` |
| [Q06.03](#q0603) | Performance by experience level | 4 | `sql/06_agent_performance/agent_performance.sql` |
| [Q06.04](#q0604) | Agents with unusually high workload | 10 | `sql/06_agent_performance/agent_performance.sql` |
| [Q06.05](#q0605) | Tickets assigned vs resolved per agent (RIGHT JOIN) | 15 | `sql/06_agent_performance/agent_performance.sql` |
| [Q06.06](#q0606) | Agent monthly trend with LAG/LEAD | 24 | `sql/06_agent_performance/agent_performance.sql` |
| [Q06.07](#q0607) | Quartiles of agents by SLA compliance (NTILE) | 4 | `sql/06_agent_performance/agent_performance.sql` |
| [Q07.01](#q0701) | Operational KPIs overall | 1 | `sql/07_business_operations/business_operations.sql` |
| [Q07.02](#q0702) | Process performance ranked by failure rate | 13 | `sql/07_business_operations/business_operations.sql` |
| [Q07.03](#q0703) | Operational cost by department | 6 | `sql/07_business_operations/business_operations.sql` |
| [Q07.04](#q0704) | Days in degraded or critical state by process and year | 10 | `sql/07_business_operations/business_operations.sql` |
| [Q07.05](#q0705) | Peak-season processing time | 13 | `sql/07_business_operations/business_operations.sql` |
| [Q07.06](#q0706) | Departmental cost by category and year | 6 | `sql/07_business_operations/business_operations.sql` |
| [Q07.07](#q0707) | Spend vs budget by department and year | 18 | `sql/07_business_operations/business_operations.sql` |
| [Q07.08](#q0708) | Cost per resolved ticket by department and year | 18 | `sql/07_business_operations/business_operations.sql` |
| [Q08.01](#q0801) | Monthly tickets: running total, 3-month moving average, MoM % | 36 | `sql/08_advanced_analytics/advanced_analytics.sql` |
| [Q08.02](#q0802) | Year-over-year KPI comparison by month | 12 | `sql/08_advanced_analytics/advanced_analytics.sql` |
| [Q08.03](#q0803) | SLA breach analysis by department, priority and year | 15 | `sql/08_advanced_analytics/advanced_analytics.sql` |
| [Q08.04](#q0804) | Departmental benchmarking against company average | 6 | `sql/08_advanced_analytics/advanced_analytics.sql` |
| [Q08.05](#q0805) | Monthly backlog reconstruction | 12 | `sql/08_advanced_analytics/advanced_analytics.sql` |
| [Q08.06](#q0806) | Repeat contact analysis (7-day window) | 8 | `sql/08_advanced_analytics/advanced_analytics.sql` |
| [Q08.07](#q0807) | Customer value x experience segmentation | 9 | `sql/08_advanced_analytics/advanced_analytics.sql` |
| [Q08.08](#q0808) | Payment Reconciliation before vs after April 2025 | 2 | `sql/08_advanced_analytics/advanced_analytics.sql` |
| [Q08.09](#q0809) | Cost efficiency trend: cost per transaction, 3-month moving average | 12 | `sql/08_advanced_analytics/advanced_analytics.sql` |
| [Q08.10](#q0810) | Agent percentile ranking (PERCENT_RANK, CUME_DIST) | 10 | `sql/08_advanced_analytics/advanced_analytics.sql` |
| [Q08.11](#q0811) | Headline KPI summary (matches Python KPI engine) | 1 | `sql/08_advanced_analytics/advanced_analytics.sql` |

### DQ.01

**Row counts per table**

* **Business question:** Did every table load with the expected number of rows?
* **Techniques:** UNION ALL, COUNT
* **Result:** 9 rows in 115 ms

<details><summary>SQL</summary>

```sql
SELECT 'customers' AS table_name, COUNT(*) AS row_count FROM support.customers
UNION ALL SELECT 'agents', COUNT(*) FROM support.agents
UNION ALL SELECT 'departments', COUNT(*) FROM support.departments
UNION ALL SELECT 'support_tickets', COUNT(*) FROM support.support_tickets
UNION ALL SELECT 'customer_feedback', COUNT(*) FROM support.customer_feedback
UNION ALL SELECT 'operations', COUNT(*) FROM support.operations
UNION ALL SELECT 'agent_performance', COUNT(*) FROM support.agent_performance
UNION ALL SELECT 'business_costs', COUNT(*) FROM support.business_costs
UNION ALL SELECT 'calendar', COUNT(*) FROM support.calendar
ORDER BY table_name;
```

</details>

| table_name | row_count |
|---|---|
| agent_performance | 1984 |
| agents | 60 |
| business_costs | 1296 |
| calendar | 1826 |
| customer_feedback | 12466 |
| customers | 3200 |

### DQ.02

**Orphan foreign keys (LEFT JOIN anti-join)**

* **Business question:** Does every ticket and survey point to an existing parent record?
* **Techniques:** LEFT JOIN, IS NULL anti-join, UNION ALL
* **Result:** 3 rows in 16 ms

<details><summary>SQL</summary>

```sql
SELECT 'tickets -> customers' AS relationship, COUNT(*) AS violations
FROM support.support_tickets t LEFT JOIN support.customers c ON c.customer_id = t.customer_id WHERE c.customer_id IS NULL
UNION ALL
SELECT 'tickets -> agents (non-null)', COUNT(*)
FROM support.support_tickets t LEFT JOIN support.agents a ON a.agent_id = t.agent_id WHERE t.agent_id IS NOT NULL AND a.agent_id IS NULL
UNION ALL
SELECT 'feedback -> tickets', COUNT(*)
FROM support.customer_feedback f LEFT JOIN support.support_tickets t ON t.ticket_id = f.ticket_id WHERE t.ticket_id IS NULL;
```

</details>

| relationship | violations |
|---|---|
| tickets -> agents (non-null) | 0 |
| tickets -> customers | 0 |
| feedback -> tickets | 0 |

### DQ.03

**Ticket chronology and status consistency**

* **Business question:** Are there impossible timestamps or open tickets with resolution dates?
* **Techniques:** CASE WHEN inside SUM (conditional aggregation)
* **Result:** 1 rows in 6 ms

<details><summary>SQL</summary>

```sql
SELECT SUM(CASE WHEN first_response_date < ticket_created_date THEN 1 ELSE 0 END) AS response_before_created,
       SUM(CASE WHEN resolved_date < ticket_created_date THEN 1 ELSE 0 END)       AS resolved_before_created,
       SUM(CASE WHEN resolved_date < first_response_date THEN 1 ELSE 0 END)       AS resolved_before_response,
       SUM(CASE WHEN ticket_status IN ('Open','In Progress','Pending','Cancelled') AND resolved_date IS NOT NULL THEN 1 ELSE 0 END) AS unresolved_with_resolution_date,
       SUM(CASE WHEN ticket_status IN ('Closed','Resolved') AND resolved_date IS NULL AND NOT resolution_ts_invalid THEN 1 ELSE 0 END) AS resolved_missing_date_unflagged
FROM support.support_tickets;
```

</details>

| response_before_created | resolved_before_created | resolved_before_response | unresolved_with_resolution_date | resolved_missing_date_unflagged |
|---|---|---|---|---|
| 0 | 0 | 0 | 0 | 0 |

### DQ.04

**Feedback consistency with its ticket**

* **Business question:** Does each survey's customer match the ticket's customer, and come after resolution?
* **Techniques:** INNER JOIN, conditional aggregation
* **Result:** 1 rows in 9 ms

<details><summary>SQL</summary>

```sql
SELECT COUNT(*) FILTER (WHERE f.customer_id <> t.customer_id)                      AS customer_mismatch,
       COUNT(*) FILTER (WHERE t.resolved_date IS NOT NULL AND f.feedback_date < t.resolved_date) AS survey_before_resolution,
       COUNT(*) FILTER (WHERE f.satisfaction_score IS NULL)                         AS missing_csat,
       COUNT(*) FILTER (WHERE f.satisfaction_score_invalid)                         AS flagged_invalid_csat
FROM support.customer_feedback f JOIN support.support_tickets t ON t.ticket_id = f.ticket_id;
```

</details>

| customer_mismatch | survey_before_resolution | missing_csat | flagged_invalid_csat |
|---|---|---|---|
| 0 | 0 | 150 | 40 |

### DQ.05

**Duplicate business keys**

* **Business question:** Are there duplicate tickets or duplicate operations days per process?
* **Techniques:** GROUP BY ... HAVING COUNT(*) > 1
* **Result:** 2 rows in 10 ms

<details><summary>SQL</summary>

```sql
SELECT 'operations (date, process)' AS key_name, COUNT(*) AS duplicate_keys
FROM (SELECT operation_date, process_name FROM support.operations GROUP BY 1, 2 HAVING COUNT(*) > 1) x
UNION ALL
SELECT 'agent_performance (agent, month)', COUNT(*)
FROM (SELECT agent_id, performance_date FROM support.agent_performance GROUP BY 1, 2 HAVING COUNT(*) > 1) y;
```

</details>

| key_name | duplicate_keys |
|---|---|
| operations (date, process) | 0 |
| agent_performance (agent, month) | 0 |

### DQ.06

**Tickets created before customer registration or agent hire**

* **Business question:** Are any tickets dated before the customer existed or the agent was hired?
* **Techniques:** multi-table JOIN, date comparison
* **Result:** 1 rows in 15 ms

<details><summary>SQL</summary>

```sql
SELECT COUNT(*) FILTER (WHERE t.ticket_created_date::date < c.registration_date) AS before_registration,
       COUNT(*) FILTER (WHERE t.ticket_created_date::date < a.hire_date)         AS before_agent_hire
FROM support.support_tickets t
JOIN support.customers c ON c.customer_id = t.customer_id
LEFT JOIN support.agents a ON a.agent_id = t.agent_id;
```

</details>

| before_registration | before_agent_hire |
|---|---|
| 0 | 0 |

### DQ.07

**Cleaning flags carried into the database**

* **Business question:** How many records carry a cleaning flag (kept but treated specially)?
* **Techniques:** scalar subqueries
* **Result:** 1 rows in 16 ms

<details><summary>SQL</summary>

```sql
SELECT (SELECT COUNT(*) FROM support.support_tickets WHERE agent_unknown)         AS tickets_unknown_agent,
       (SELECT COUNT(*) FROM support.support_tickets WHERE resolution_ts_invalid) AS tickets_invalid_resolution_ts,
       (SELECT COUNT(*) FROM support.support_tickets WHERE first_response_missing) AS tickets_missing_first_response,
       (SELECT COUNT(*) FROM support.customers WHERE clv_imputed)                 AS customers_clv_imputed,
       (SELECT COUNT(*) FROM support.operations WHERE cost_outlier)               AS ops_cost_outliers_replaced,
       (SELECT COUNT(*) FROM support.operations WHERE processing_time_imputed)    AS ops_processing_time_imputed;
```

</details>

| tickets_unknown_agent | tickets_invalid_resolution_ts | tickets_missing_first_response | customers_clv_imputed | ops_cost_outliers_replaced | ops_processing_time_imputed |
|---|---|---|---|---|---|
| 15 | 25 | 90 | 70 | 18 | 70 |

### DQ.08

**Calendar coverage**

* **Business question:** Does the date dimension cover every ticket date without gaps?
* **Techniques:** LEAD window function for gap detection, scalar subqueries
* **Result:** 1 rows in 10 ms

<details><summary>SQL</summary>

```sql
SELECT (SELECT MIN(date) FROM support.calendar) AS calendar_start,
       (SELECT MAX(date) FROM support.calendar) AS calendar_end,
       (SELECT COUNT(*) FROM (SELECT date, LEAD(date) OVER (ORDER BY date) - date AS gap FROM support.calendar) g WHERE gap > 1) AS gaps,
       (SELECT COUNT(*) FROM support.support_tickets t WHERE NOT EXISTS
            (SELECT 1 FROM support.calendar c WHERE c.date = t.ticket_created_date::date)) AS ticket_dates_missing;
```

</details>

| calendar_start | calendar_end | gaps | ticket_dates_missing |
|---|---|---|---|
| 2021-01-01 | 2025-12-31 | 0 | 0 |

### Q04.01

**Customer base by segment**

* **Business question:** How are customers and lifetime value distributed across segments?
* **Techniques:** SELECT, GROUP BY, ORDER BY, aggregate functions
* **Result:** 4 rows in 4 ms

<details><summary>SQL</summary>

```sql
SELECT customer_segment,
       COUNT(*)                                    AS customers,
       ROUND(AVG(customer_lifetime_value), 0)      AS avg_clv,
       ROUND((PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY customer_lifetime_value))::numeric, 0) AS median_clv,
       ROUND(SUM(customer_lifetime_value), 0)      AS total_clv
FROM support.customers
GROUP BY customer_segment
ORDER BY total_clv DESC;
```

</details>

| customer_segment | customers | avg_clv | median_clv | total_clv |
|---|---|---|---|---|
| Enterprise | 394 | 48,925.00 | 42,570.00 | 19,276,453.00 |
| Mid-Market | 742 | 14,268.00 | 12,298.00 | 10,586,738.00 |
| Small Business | 951 | 4,405.00 | 3,614.00 | 4,189,606.00 |
| Consumer | 1113 | 794.00 | 637.00 | 883,256.00 |

### Q04.02

**Customers by region and country**

* **Business question:** Which regions and countries hold the most customers?
* **Techniques:** WHERE, GROUP BY, HAVING, ORDER BY
* **Result:** 15 rows in 3 ms

<details><summary>SQL</summary>

```sql
SELECT customer_region, customer_country, COUNT(*) AS customers
FROM support.customers
WHERE customer_status <> 'Churned'
GROUP BY customer_region, customer_country
HAVING COUNT(*) >= 50
ORDER BY customer_region, customers DESC;
```

</details>

| customer_region | customer_country | customers |
|---|---|---|
| Asia Pacific | Australia | 175 |
| Asia Pacific | India | 158 |
| Asia Pacific | Japan | 105 |
| Asia Pacific | Singapore | 80 |
| Asia Pacific | Philippines | 60 |
| Europe | United Kingdom | 228 |

### Q04.03

**New customer registrations per year**

* **Business question:** How fast is the customer base growing?
* **Techniques:** DATE_PART, GROUP BY, LAG for year-over-year growth
* **Result:** 5 rows in 3 ms

<details><summary>SQL</summary>

```sql
SELECT reg_year, new_customers,
       ROUND(100.0 * (new_customers - LAG(new_customers) OVER (ORDER BY reg_year))
             / NULLIF(LAG(new_customers) OVER (ORDER BY reg_year), 0), 1) AS yoy_growth_pct
FROM (SELECT DATE_PART('year', registration_date)::int AS reg_year, COUNT(*) AS new_customers
      FROM support.customers GROUP BY 1) y
ORDER BY reg_year;
```

</details>

| reg_year | new_customers | yoy_growth_pct |
|---|---|---|
| 2021 | 631 |  |
| 2022 | 809 | 28.20 |
| 2023 | 786 | -2.80 |
| 2024 | 643 | -18.20 |
| 2025 | 331 | -48.50 |

### Q04.04

**Distinct contacting customers per year**

* **Business question:** How many distinct customers contacted support each year?
* **Techniques:** COUNT(DISTINCT), DATE_TRUNC
* **Result:** 3 rows in 28 ms

<details><summary>SQL</summary>

```sql
SELECT DATE_PART('year', ticket_created_date)::int AS year,
       COUNT(DISTINCT customer_id)                 AS contacting_customers,
       COUNT(*)                                    AS tickets,
       ROUND(COUNT(*)::numeric / COUNT(DISTINCT customer_id), 2) AS tickets_per_contacting_customer
FROM support.support_tickets
GROUP BY 1 ORDER BY 1;
```

</details>

| year | contacting_customers | tickets | tickets_per_contacting_customer |
|---|---|---|---|
| 2023 | 1490 | 7226 | 4.85 |
| 2024 | 1887 | 8071 | 4.28 |
| 2025 | 2123 | 8703 | 4.10 |

### Q04.05

**Customer contact-frequency segmentation**

* **Business question:** How many customers are light, regular or heavy support users, and what is their value?
* **Techniques:** CTE, CASE WHEN bucketing, LEFT JOIN (customers without tickets)
* **Result:** 4 rows in 14 ms

<details><summary>SQL</summary>

```sql
WITH per_customer AS (
    SELECT c.customer_id, c.customer_segment, c.customer_lifetime_value, COUNT(t.ticket_id) AS tickets
    FROM support.customers c
    LEFT JOIN support.support_tickets t ON t.customer_id = c.customer_id
    GROUP BY c.customer_id, c.customer_segment, c.customer_lifetime_value
)
SELECT CASE WHEN tickets = 0 THEN '0 - never contacted'
            WHEN tickets <= 3 THEN '1-3 - light'
            WHEN tickets <= 10 THEN '4-10 - regular'
            ELSE '11+ - heavy' END AS contact_band,
       COUNT(*) AS customers,
       ROUND(AVG(customer_lifetime_value), 0) AS avg_clv,
       SUM(tickets) AS tickets
FROM per_customer
GROUP BY 1 ORDER BY 1;
```

</details>

| contact_band | customers | avg_clv | tickets |
|---|---|---|---|
| 0 - never contacted | 607 | 5,311.00 | 0.00 |
| 1-3 - light | 1021 | 7,652.00 | 1,862.00 |
| 11+ - heavy | 679 | 20,644.00 | 16,526.00 |
| 4-10 - regular | 893 | 11,067.00 | 5,612.00 |

### Q04.06

**Top 15 customers by ticket volume (repeat contacts)**

* **Business question:** Which customers generate the most repeated support requests?
* **Techniques:** view reuse, GROUP BY, ORDER BY ... LIMIT
* **Result:** 15 rows in 88 ms

<details><summary>SQL</summary>

```sql
SELECT customer_id, customer_segment, customer_region, tickets, repeat_contacts, escalations, avg_csat,
       customer_lifetime_value
FROM support.v_customer_360
ORDER BY tickets DESC, repeat_contacts DESC
LIMIT 15;
```

</details>

| customer_id | customer_segment | customer_region | tickets | repeat_contacts | escalations | avg_csat | customer_lifetime_value |
|---|---|---|---|---|---|---|---|
| CUS-00003 | Enterprise | North America | 256 | 218 | 16 | 3.80 | 31,687.31 |
| CUS-01324 | Enterprise | Europe | 154 | 93 | 16 | 3.52 | 43,846.08 |
| CUS-00209 | Enterprise | North America | 125 | 66 | 18 | 3.68 | 36,002.93 |
| CUS-02982 | Enterprise | North America | 122 | 65 | 14 | 3.82 | 40,831.09 |
| CUS-00697 | Enterprise | Europe | 101 | 46 | 11 | 3.77 | 36,680.77 |
| CUS-02888 | Enterprise | Latin America | 94 | 46 | 8 | 3.65 | 40,396.88 |

### Q04.07

**Support experience by customer status**

* **Business question:** Do churned customers show worse support experience than active ones?
* **Techniques:** INNER JOIN to view, conditional aggregation
* **Result:** 3 rows in 58 ms

<details><summary>SQL</summary>

```sql
SELECT c.customer_status,
       COUNT(*) AS tickets,
       ROUND(AVG(v.satisfaction_score)::numeric, 2) AS avg_csat,
       ROUND(100.0 * COUNT(*) FILTER (WHERE v.sla_met) / NULLIF(COUNT(*) FILTER (WHERE v.sla_eligible), 0), 2) AS sla_pct,
       ROUND(100.0 * COUNT(*) FILTER (WHERE v.is_escalated) / COUNT(*), 2) AS escalation_pct
FROM support.v_ticket_metrics v
JOIN support.customers c ON c.customer_id = v.customer_id
GROUP BY c.customer_status
ORDER BY avg_csat;
```

</details>

| customer_status | tickets | avg_csat | sla_pct | escalation_pct |
|---|---|---|---|---|
| Churned | 2444 | 3.66 | 71.13 | 11.21 |
| Active | 21022 | 3.76 | 73.04 | 9.93 |
| Inactive | 534 | 3.76 | 76.20 | 7.68 |

### Q04.08

**Customers whose CSAT is below their segment average**

* **Business question:** Which high-value customers are less satisfied than their peers?
* **Techniques:** correlated subquery, HAVING
* **Result:** 15 rows in 1424 ms

<details><summary>SQL</summary>

```sql
SELECT c.customer_id, c.customer_segment, c.customer_lifetime_value,
       ROUND(AVG(f.satisfaction_score)::numeric, 2) AS avg_csat, COUNT(f.feedback_id) AS surveys
FROM support.customers c
JOIN support.customer_feedback f ON f.customer_id = c.customer_id
WHERE c.customer_lifetime_value > (SELECT PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY customer_lifetime_value)
                                   FROM support.customers c2 WHERE c2.customer_segment = c.customer_segment)
GROUP BY c.customer_id, c.customer_segment, c.customer_lifetime_value
HAVING COUNT(f.feedback_id) >= 3
   AND AVG(f.satisfaction_score) < (SELECT AVG(f2.satisfaction_score) FROM support.customer_feedback f2
                                    JOIN support.customers c3 ON c3.customer_id = f2.customer_id
                                    WHERE c3.customer_segment = c.customer_segment)
ORDER BY c.customer_lifetime_value DESC
LIMIT 15;
```

</details>

| customer_id | customer_segment | customer_lifetime_value | avg_csat | surveys |
|---|---|---|---|---|
| CUS-02714 | Enterprise | 150,671.18 | 3.40 | 5 |
| CUS-01604 | Enterprise | 121,150.61 | 3.54 | 39 |
| CUS-01845 | Enterprise | 111,628.21 | 3.69 | 14 |
| CUS-03034 | Enterprise | 110,197.66 | 3.58 | 12 |
| CUS-02779 | Enterprise | 105,601.41 | 3.40 | 11 |
| CUS-01612 | Enterprise | 99,741.37 | 3.00 | 9 |

### Q05.01

**Ticket status distribution**

* **Business question:** What share of tickets is in each status at the snapshot date?
* **Techniques:** GROUP BY, window SUM() OVER () for share of total
* **Result:** 6 rows in 5 ms

<details><summary>SQL</summary>

```sql
SELECT ticket_status, COUNT(*) AS tickets,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS share_pct
FROM support.support_tickets
GROUP BY ticket_status
ORDER BY tickets DESC;
```

</details>

| ticket_status | tickets | share_pct |
|---|---|---|
| Closed | 21229 | 88.45 |
| Resolved | 2007 | 8.36 |
| Cancelled | 507 | 2.11 |
| In Progress | 124 | 0.52 |
| Pending | 89 | 0.37 |
| Open | 44 | 0.18 |

### Q05.02

**Ticket volume by category and subcategory**

* **Business question:** Which categories and subcategories generate the most workload?
* **Techniques:** GROUP BY ROLLUP, ORDER BY
* **Result:** 43 rows in 7 ms

<details><summary>SQL</summary>

```sql
SELECT COALESCE(ticket_category, 'ALL') AS category, COALESCE(ticket_subcategory, 'Subtotal') AS subcategory,
       COUNT(*) AS tickets
FROM support.support_tickets
GROUP BY ROLLUP (ticket_category, ticket_subcategory)
ORDER BY ticket_category NULLS LAST, tickets DESC;
```

</details>

| category | subcategory | tickets |
|---|---|---|
| Account Access | Subtotal | 2578 |
| Account Access | Password Reset | 658 |
| Account Access | Account Locked | 654 |
| Account Access | 2FA Problem | 643 |
| Account Access | Permission Change | 623 |
| Billing & Payment | Subtotal | 4885 |

### Q05.03

**Response and resolution by channel**

* **Business question:** Which support channels have the longest response and resolution times?
* **Techniques:** reporting view, ORDER BY
* **Result:** 6 rows in 31 ms

<details><summary>SQL</summary>

```sql
SELECT * FROM support.v_channel_performance ORDER BY avg_frt_h DESC;
```

</details>

| support_channel | tickets | avg_frt_h | avg_resolution_h | sla_compliance_pct | fcr_pct | avg_csat |
|---|---|---|---|---|---|---|
| Web Portal | 3179 | 13.47 | 48.69 | 58.55 | 11.37 | 3.32 |
| Email | 7885 | 10.29 | 44.26 | 63.21 | 13.57 | 3.47 |
| Social Media | 1684 | 7.53 | 44.11 | 65.33 | 14.50 | 3.37 |
| Unknown | 120 | 3.85 | 33.68 | 69.30 | 14.04 | 3.53 |
| Live Chat | 5849 | 0.13 | 23.03 | 84.33 | 29.49 | 4.13 |
| Phone | 5283 | 0.08 | 20.78 | 85.96 | 32.97 | 4.16 |

### Q05.04

**Resolution time by priority vs SLA target**

* **Business question:** Which priorities take longest relative to their SLA targets?
* **Techniques:** AVG / PERCENTILE_CONT with FILTER, CASE ordering
* **Result:** 4 rows in 28 ms

<details><summary>SQL</summary>

```sql
SELECT ticket_priority, MIN(sla_target_hours) AS sla_target_h,
       COUNT(*) FILTER (WHERE sla_eligible) AS resolved,
       ROUND((AVG(resolution_hours) FILTER (WHERE sla_eligible))::numeric, 2) AS avg_resolution_h,
       ROUND((PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY resolution_hours) FILTER (WHERE sla_eligible))::numeric, 2) AS median_resolution_h,
       ROUND((PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY resolution_hours) FILTER (WHERE sla_eligible))::numeric, 2) AS p90_resolution_h,
       ROUND(100.0 * COUNT(*) FILTER (WHERE sla_met) / COUNT(*) FILTER (WHERE sla_eligible), 2) AS sla_compliance_pct
FROM support.v_ticket_metrics
GROUP BY ticket_priority
ORDER BY CASE ticket_priority WHEN 'Critical' THEN 1 WHEN 'High' THEN 2 WHEN 'Medium' THEN 3 ELSE 4 END;
```

</details>

| ticket_priority | sla_target_h | resolved | avg_resolution_h | median_resolution_h | p90_resolution_h | sla_compliance_pct |
|---|---|---|---|---|---|---|
| Critical | 8 | 1600 | 11.44 | 7.03 | 27.06 | 54.69 |
| High | 24 | 5804 | 21.20 | 14.96 | 47.06 | 69.37 |
| Medium | 48 | 9181 | 36.39 | 25.38 | 81.32 | 74.47 |
| Low | 72 | 6626 | 48.94 | 34.41 | 110.15 | 78.27 |

### Q05.05

**Ticket volume by weekday and hour band**

* **Business question:** When does demand peak during the week?
* **Techniques:** EXTRACT(ISODOW/HOUR), CASE bucketing, conditional aggregation (pivot)
* **Result:** 7 rows in 18 ms

<details><summary>SQL</summary>

```sql
SELECT TO_CHAR(ticket_created_date, 'ID-Dy') AS weekday,
       COUNT(*) FILTER (WHERE EXTRACT(HOUR FROM ticket_created_date) < 8)                 AS "00-08",
       COUNT(*) FILTER (WHERE EXTRACT(HOUR FROM ticket_created_date) BETWEEN 8 AND 11)    AS "08-12",
       COUNT(*) FILTER (WHERE EXTRACT(HOUR FROM ticket_created_date) BETWEEN 12 AND 16)   AS "12-17",
       COUNT(*) FILTER (WHERE EXTRACT(HOUR FROM ticket_created_date) BETWEEN 17 AND 19)   AS "17-20",
       COUNT(*) FILTER (WHERE EXTRACT(HOUR FROM ticket_created_date) >= 20)               AS "20-24",
       COUNT(*) AS total
FROM support.support_tickets
GROUP BY 1 ORDER BY 1;
```

</details>

| weekday | 00-08 | 08-12 | 12-17 | 17-20 | 20-24 | total |
|---|---|---|---|---|---|---|
| 1-Mon | 360 | 1428 | 1789 | 628 | 320 | 4525 |
| 2-Tue | 316 | 1242 | 1615 | 551 | 309 | 4033 |
| 3-Wed | 295 | 1268 | 1664 | 568 | 321 | 4116 |
| 4-Thu | 271 | 1165 | 1566 | 590 | 274 | 3866 |
| 5-Fri | 235 | 1130 | 1414 | 528 | 255 | 3562 |
| 6-Sat | 133 | 661 | 854 | 305 | 163 | 2116 |

### Q05.06

**Escalations and reopenings by category**

* **Business question:** Which categories drive escalations and reopened tickets?
* **Techniques:** conditional aggregation, NULLIF for safe division
* **Result:** 8 rows in 13 ms

<details><summary>SQL</summary>

```sql
SELECT ticket_category,
       COUNT(*) AS tickets,
       COUNT(*) FILTER (WHERE is_escalated) AS escalated,
       ROUND(100.0 * COUNT(*) FILTER (WHERE is_escalated) / NULLIF(COUNT(*) FILTER (WHERE NOT is_cancelled), 0), 2) AS escalation_pct,
       COUNT(*) FILTER (WHERE is_reopened) AS reopened,
       ROUND(100.0 * COUNT(*) FILTER (WHERE is_reopened) / NULLIF(COUNT(*) FILTER (WHERE is_resolved), 0), 2) AS reopen_pct
FROM support.v_ticket_metrics
GROUP BY ticket_category
ORDER BY escalation_pct DESC;
```

</details>

| ticket_category | tickets | escalated | escalation_pct | reopened | reopen_pct |
|---|---|---|---|---|---|
| Complaint | 976 | 225 | 23.54 | 122 | 12.87 |
| Technical Issue | 5558 | 845 | 15.54 | 502 | 9.34 |
| Delivery Problem | 2719 | 292 | 10.97 | 210 | 7.98 |
| Returns & Refunds | 2832 | 302 | 10.91 | 400 | 14.58 |
| Billing & Payment | 4885 | 454 | 9.48 | 453 | 9.59 |
| Order Status | 3084 | 162 | 5.39 | 135 | 4.54 |

### Q05.07

**First contact resolution by channel and category**

* **Business question:** Where are tickets solved in a single interaction?
* **Techniques:** GROUP BY two dimensions, HAVING on volume
* **Result:** 15 rows in 15 ms

<details><summary>SQL</summary>

```sql
SELECT support_channel, ticket_category,
       COUNT(*) FILTER (WHERE sla_eligible) AS resolved,
       ROUND(100.0 * COUNT(*) FILTER (WHERE is_fcr) / NULLIF(COUNT(*) FILTER (WHERE sla_eligible), 0), 2) AS fcr_pct
FROM support.v_ticket_metrics
WHERE support_channel <> 'Unknown'
GROUP BY support_channel, ticket_category
HAVING COUNT(*) FILTER (WHERE sla_eligible) >= 100
ORDER BY fcr_pct DESC
LIMIT 15;
```

</details>

| support_channel | ticket_category | resolved | fcr_pct |
|---|---|---|---|
| Phone | Product Inquiry | 268 | 69.40 |
| Phone | Account Access | 565 | 65.13 |
| Live Chat | Product Inquiry | 345 | 61.45 |
| Live Chat | Account Access | 601 | 60.07 |
| Phone | Order Status | 633 | 45.97 |
| Live Chat | Order Status | 745 | 42.28 |

### Q05.08

**Open backlog by aging bucket**

* **Business question:** How old is the open backlog and how much of it is already past SLA?
* **Techniques:** reporting view, ORDER BY
* **Result:** 6 rows in 6 ms

<details><summary>SQL</summary>

```sql
SELECT * FROM support.v_backlog_aging ORDER BY aging_bucket;
```

</details>

| aging_bucket | open_tickets | never_responded | past_sla_target |
|---|---|---|---|
| 1. 0-2 days | 35 | 6 | 0 |
| 2. 3-7 days | 18 | 1 | 17 |
| 3. 8-14 days | 19 | 0 | 19 |
| 4. 15-30 days | 30 | 5 | 30 |
| 5. 31-60 days | 45 | 12 | 45 |
| 6. 60+ days | 110 | 20 | 110 |

### Q05.09

**Oldest open tickets (aging list)**

* **Business question:** Which open tickets have waited longest and who owns them?
* **Techniques:** multi-table JOIN, LEFT JOIN for unknown agents, ORDER BY ... LIMIT
* **Result:** 15 rows in 6 ms

<details><summary>SQL</summary>

```sql
SELECT v.ticket_id, v.ticket_status, v.ticket_priority, v.ticket_category, v.department_name,
       COALESCE(v.agent_name, '(unassigned / unknown)') AS agent, ROUND(v.ticket_age_days::numeric, 1) AS age_days
FROM support.v_ticket_metrics v
WHERE v.is_unresolved
ORDER BY v.ticket_age_days DESC
LIMIT 15;
```

</details>

| ticket_id | ticket_status | ticket_priority | ticket_category | department_name | agent | age_days |
|---|---|---|---|---|---|---|
| TCK-014427 | In Progress | Medium | Order Status | Order Management | Debra Davidson | 394.10 |
| TCK-014522 | Pending | Medium | Delivery Problem | Logistics & Delivery | Shane Henderson | 391.20 |
| TCK-014728 | In Progress | Medium | Delivery Problem | Logistics & Delivery | Anthony Humphrey | 384.40 |
| TCK-014730 | Pending | High | Order Status | Order Management | Elizabeth Fowler | 384.40 |
| TCK-015073 | Pending | Critical | Technical Issue | Technical Support | Holly Wood | 372.40 |
| TCK-015096 | Pending | Low | Technical Issue | Technical Support | Dylan Miller | 371.70 |

### Q05.10

**CSAT by first response time band**

* **Business question:** Is customer satisfaction associated with how fast the first response arrives?
* **Techniques:** CASE bucketing, AVG, ordering by band
* **Result:** 6 rows in 19 ms

<details><summary>SQL</summary>

```sql
SELECT CASE WHEN first_response_hours < 0.25 THEN '1. <15 min'
            WHEN first_response_hours < 1    THEN '2. 15-60 min'
            WHEN first_response_hours < 4    THEN '3. 1-4 h'
            WHEN first_response_hours < 8    THEN '4. 4-8 h'
            WHEN first_response_hours < 24   THEN '5. 8-24 h'
            ELSE '6. 24 h+' END AS frt_band,
       COUNT(*) AS surveys,
       ROUND(AVG(satisfaction_score)::numeric, 3) AS avg_csat,
       ROUND(100.0 * COUNT(*) FILTER (WHERE satisfaction_score >= 4) / COUNT(*), 2) AS satisfied_pct
FROM support.v_ticket_metrics
WHERE satisfaction_score IS NOT NULL AND first_response_hours IS NOT NULL
GROUP BY 1 ORDER BY 1;
```

</details>

| frt_band | surveys | avg_csat | satisfied_pct |
|---|---|---|---|
| 1. <15 min | 5130 | 4.14 | 79.90 |
| 2. 15-60 min | 844 | 3.98 | 72.27 |
| 3. 1-4 h | 1765 | 3.65 | 59.26 |
| 4. 4-8 h | 1493 | 3.50 | 53.52 |
| 5. 8-24 h | 2263 | 3.30 | 44.14 |
| 6. 24 h+ | 769 | 2.95 | 29.00 |

### Q05.11

**CSAT by channel with SLA outcome**

* **Business question:** Does an SLA breach hurt satisfaction equally on every channel?
* **Techniques:** conditional AVG with FILTER, derived difference column
* **Result:** 5 rows in 31 ms

<details><summary>SQL</summary>

```sql
SELECT support_channel,
       ROUND((AVG(satisfaction_score) FILTER (WHERE sla_met))::numeric, 2)          AS csat_within_sla,
       ROUND((AVG(satisfaction_score) FILTER (WHERE sla_met = FALSE))::numeric, 2)  AS csat_breached,
       ROUND((AVG(satisfaction_score) FILTER (WHERE sla_met) - AVG(satisfaction_score) FILTER (WHERE sla_met = FALSE))::numeric, 2) AS csat_gap
FROM support.v_ticket_metrics
WHERE support_channel <> 'Unknown'
GROUP BY support_channel
ORDER BY csat_gap DESC;
```

</details>

| support_channel | csat_within_sla | csat_breached | csat_gap |
|---|---|---|---|
| Social Media | 3.89 | 2.54 | 1.35 |
| Phone | 4.39 | 3.05 | 1.34 |
| Web Portal | 3.93 | 2.63 | 1.30 |
| Live Chat | 4.36 | 3.09 | 1.27 |
| Email | 4.01 | 2.74 | 1.27 |

### Q05.12

**Feedback themes**

* **Business question:** What do customers talk about in surveys, and how satisfied is each theme?
* **Techniques:** GROUP BY, DISTINCT inside aggregate
* **Result:** 6 rows in 15 ms

<details><summary>SQL</summary>

```sql
SELECT feedback_category, COUNT(*) AS responses, COUNT(DISTINCT customer_id) AS customers,
       ROUND(AVG(satisfaction_score)::numeric, 2) AS avg_csat,
       COUNT(customer_comment) AS with_comment
FROM support.customer_feedback
GROUP BY feedback_category
ORDER BY responses DESC;
```

</details>

| feedback_category | responses | customers | avg_csat | with_comment |
|---|---|---|---|---|
| Response Speed | 3718 | 1455 | 3.22 | 2660 |
| Agent Professionalism | 2683 | 1260 | 4.17 | 1931 |
| Resolution Quality | 2472 | 1204 | 3.97 | 1792 |
| Communication | 1968 | 1071 | 4.09 | 1418 |
| Product Issue | 1086 | 681 | 3.76 | 790 |
| Process & Policy | 539 | 417 | 3.03 | 389 |

### Q06.01

**Agent scorecard**

* **Business question:** How does each agent perform on volume, speed, SLA, quality and satisfaction?
* **Techniques:** reporting view, ORDER BY
* **Result:** 20 rows in 45 ms

<details><summary>SQL</summary>

```sql
SELECT agent_name, department_name, experience_level, tickets_assigned, tickets_resolved, productivity_pct,
       avg_resolution_h, sla_compliance_pct, reopen_pct, avg_csat
FROM support.v_agent_scorecard
ORDER BY tickets_resolved DESC
LIMIT 20;
```

</details>

| agent_name | department_name | experience_level | tickets_assigned | tickets_resolved | productivity_pct | avg_resolution_h | sla_compliance_pct | reopen_pct | avg_csat |
|---|---|---|---|---|---|---|---|---|---|
| Elizabeth Fowler | Order Management | Mid-Level | 895 | 859 | 98.74 | 22.03 | 86.35 | 5.47 | 3.87 |
| Rebecca Henderson | Billing & Accounts | Senior | 828 | 799 | 98.16 | 28.05 | 78.10 | 6.63 | 3.96 |
| Paula Moreno | Logistics & Delivery | Lead | 784 | 757 | 98.44 | 36.61 | 69.89 | 5.55 | 3.62 |
| Justin Baker | Billing & Accounts | Mid-Level | 735 | 709 | 98.47 | 34.68 | 72.21 | 9.17 | 3.75 |
| Stephanie Ross | Billing & Accounts | Mid-Level | 732 | 708 | 99.02 | 38.92 | 71.57 | 10.73 | 3.77 |
| Lisa Hensley | Technical Support | Mid-Level | 721 | 705 | 99.58 | 35.99 | 69.22 | 8.23 | 3.81 |

### Q06.02

**Agent ranking within department (RANK, DENSE_RANK, ROW_NUMBER)**

* **Business question:** Who are the top performers in each department by SLA compliance?
* **Techniques:** window functions RANK / DENSE_RANK / ROW_NUMBER with PARTITION BY
* **Result:** 58 rows in 44 ms

<details><summary>SQL</summary>

```sql
WITH s AS (SELECT * FROM support.v_agent_scorecard WHERE tickets_resolved >= 100)
SELECT department_name, agent_name, experience_level, sla_compliance_pct, avg_csat,
       RANK()       OVER (PARTITION BY department_name ORDER BY sla_compliance_pct DESC) AS sla_rank,
       DENSE_RANK() OVER (PARTITION BY department_name ORDER BY ROUND(avg_csat, 1) DESC) AS csat_dense_rank,
       ROW_NUMBER() OVER (PARTITION BY department_name ORDER BY tickets_resolved DESC)   AS volume_row
FROM s
ORDER BY department_name, sla_rank;
```

</details>

| department_name | agent_name | experience_level | sla_compliance_pct | avg_csat | sla_rank | csat_dense_rank | volume_row |
|---|---|---|---|---|---|---|---|
| Billing & Accounts | Matthew Foster | Lead | 90.26 | 3.79 | 1 | 3 | 7 |
| Billing & Accounts | Tommy Walter | Lead | 89.19 | 3.72 | 2 | 4 | 8 |
| Billing & Accounts | Judy Baker | Senior | 79.79 | 3.94 | 3 | 2 | 6 |
| Billing & Accounts | Rebecca Henderson | Senior | 78.10 | 3.96 | 4 | 1 | 1 |
| Billing & Accounts | Justin Baker | Mid-Level | 72.21 | 3.75 | 5 | 3 | 2 |
| Billing & Accounts | Stephanie Ross | Mid-Level | 71.57 | 3.77 | 6 | 3 | 3 |

### Q06.03

**Performance by experience level**

* **Business question:** How do Junior, Mid-Level, Senior and Lead agents compare?
* **Techniques:** GROUP BY, CASE ordering
* **Result:** 4 rows in 54 ms

<details><summary>SQL</summary>

```sql
SELECT experience_level, COUNT(DISTINCT agent_id) AS agents, COUNT(*) AS tickets,
       ROUND((AVG(resolution_hours) FILTER (WHERE sla_eligible))::numeric, 2) AS avg_resolution_h,
       ROUND(100.0 * COUNT(*) FILTER (WHERE sla_met) / COUNT(*) FILTER (WHERE sla_eligible), 2) AS sla_pct,
       ROUND(100.0 * COUNT(*) FILTER (WHERE is_reopened) / COUNT(*) FILTER (WHERE is_resolved), 2) AS reopen_pct,
       ROUND(AVG(satisfaction_score)::numeric, 2) AS avg_csat
FROM support.v_ticket_metrics
WHERE agent_id IS NOT NULL
GROUP BY experience_level
ORDER BY CASE experience_level WHEN 'Junior' THEN 1 WHEN 'Mid-Level' THEN 2 WHEN 'Senior' THEN 3 ELSE 4 END;
```

</details>

| experience_level | agents | tickets | avg_resolution_h | sla_pct | reopen_pct | avg_csat |
|---|---|---|---|---|---|---|
| Junior | 9 | 2748 | 58.83 | 53.23 | 16.58 | 3.41 |
| Mid-Level | 23 | 9257 | 34.63 | 72.01 | 8.75 | 3.74 |
| Senior | 17 | 7707 | 29.27 | 76.80 | 6.33 | 3.82 |
| Lead | 11 | 4273 | 27.80 | 80.42 | 5.67 | 3.88 |

### Q06.04

**Agents with unusually high workload**

* **Business question:** Which agents carry a monthly workload well above their department average?
* **Techniques:** CTE, AVG() OVER (PARTITION BY), HAVING-style filter on window result
* **Result:** 10 rows in 3 ms

<details><summary>SQL</summary>

```sql
WITH monthly AS (
    SELECT p.agent_id, a.agent_name, a.department_id, AVG(p.tickets_assigned) AS avg_assigned, AVG(p.workload_hours) AS avg_hours
    FROM support.agent_performance p JOIN support.agents a USING (agent_id)
    GROUP BY p.agent_id, a.agent_name, a.department_id
), cmp AS (
    SELECT *, AVG(avg_assigned) OVER (PARTITION BY department_id) AS dept_avg
    FROM monthly
)
SELECT agent_name, department_id, ROUND(avg_assigned, 1) AS avg_tickets_per_month,
       ROUND(dept_avg, 1) AS dept_avg_tickets, ROUND(100.0 * (avg_assigned / dept_avg - 1), 1) AS pct_above_dept,
       ROUND(avg_hours, 1) AS avg_workload_hours
FROM cmp
WHERE avg_assigned > 1.25 * dept_avg
ORDER BY pct_above_dept DESC;
```

</details>

| agent_name | department_id | avg_tickets_per_month | dept_avg_tickets | pct_above_dept | avg_workload_hours |
|---|---|---|---|---|---|
| Elizabeth Fowler | DEP-03 | 24.20 | 11.00 | 120.90 | 33.00 |
| Paula Moreno | DEP-04 | 21.40 | 10.20 | 110.10 | 32.10 |
| Richard Aguirre | DEP-06 | 13.30 | 7.70 | 72.40 | 29.50 |
| Jessica Holmes | DEP-05 | 16.20 | 9.70 | 66.20 | 29.90 |
| Fred Smith | DEP-04 | 16.20 | 10.20 | 59.40 | 29.50 |
| James Ferrell | DEP-02 | 28.00 | 18.10 | 55.10 | 34.80 |

### Q06.05

**Tickets assigned vs resolved per agent (RIGHT JOIN)**

* **Business question:** Do any agents (including those with no tickets) have a gap between assigned and resolved?
* **Techniques:** RIGHT JOIN (keeps every agent), COALESCE
* **Result:** 15 rows in 8 ms

<details><summary>SQL</summary>

```sql
SELECT a.agent_id, a.agent_name, a.employment_status,
       COALESCE(x.assigned, 0) AS assigned, COALESCE(x.resolved, 0) AS resolved,
       COALESCE(x.assigned, 0) - COALESCE(x.resolved, 0) AS gap
FROM (SELECT agent_id, COUNT(*) AS assigned, COUNT(*) FILTER (WHERE ticket_status IN ('Closed','Resolved')) AS resolved
      FROM support.support_tickets GROUP BY agent_id) x
RIGHT JOIN support.agents a ON a.agent_id = x.agent_id
ORDER BY gap DESC
LIMIT 15;
```

</details>

| agent_id | agent_name | employment_status | assigned | resolved | gap |
|---|---|---|---|---|---|
| AGT-033 | Elizabeth Fowler | Active | 895 | 859 | 36 |
| AGT-025 | Rebecca Henderson | On Leave | 828 | 799 | 29 |
| AGT-035 | Paula Moreno | Active | 784 | 757 | 27 |
| AGT-021 | Justin Baker | Active | 735 | 709 | 26 |
| AGT-010 | Brian Ramirez | Active | 677 | 652 | 25 |
| AGT-022 | Stephanie Ross | Active | 732 | 708 | 24 |

### Q06.06

**Agent monthly trend with LAG/LEAD**

* **Business question:** How did each Billing agent's monthly resolutions change month to month?
* **Techniques:** LAG, LEAD, PARTITION BY agent
* **Result:** 24 rows in 2 ms

<details><summary>SQL</summary>

```sql
SELECT a.agent_name, p.performance_date, p.tickets_resolved,
       LAG(p.tickets_resolved)  OVER w AS prev_month,
       LEAD(p.tickets_resolved) OVER w AS next_month,
       p.tickets_resolved - LAG(p.tickets_resolved) OVER w AS mom_change
FROM support.agent_performance p
JOIN support.agents a USING (agent_id)
WHERE a.department_id = 'DEP-02' AND p.performance_date >= DATE '2025-01-01'
WINDOW w AS (PARTITION BY p.agent_id ORDER BY p.performance_date)
ORDER BY a.agent_name, p.performance_date
LIMIT 24;
```

</details>

| agent_name | performance_date | tickets_resolved | prev_month | next_month | mom_change |
|---|---|---|---|---|---|
| Anthony Rodriguez | 2025-01-31 | 19 |  | 12.00 |  |
| Anthony Rodriguez | 2025-02-28 | 12 | 19.00 | 12.00 | -7.00 |
| Anthony Rodriguez | 2025-03-31 | 12 | 12.00 | 35.00 | 0.00 |
| Anthony Rodriguez | 2025-04-30 | 35 | 12.00 | 37.00 | 23.00 |
| Anthony Rodriguez | 2025-05-31 | 37 | 35.00 | 34.00 | 2.00 |
| Anthony Rodriguez | 2025-06-30 | 34 | 37.00 | 17.00 | -3.00 |

### Q06.07

**Quartiles of agents by SLA compliance (NTILE)**

* **Business question:** How large is the gap between top-quartile and bottom-quartile agents?
* **Techniques:** NTILE, CTE, aggregation of window output
* **Result:** 4 rows in 45 ms

<details><summary>SQL</summary>

```sql
WITH q AS (
    SELECT *, NTILE(4) OVER (ORDER BY sla_compliance_pct DESC) AS quartile
    FROM support.v_agent_scorecard WHERE tickets_resolved >= 100
)
SELECT quartile, COUNT(*) AS agents, ROUND(AVG(sla_compliance_pct), 2) AS avg_sla_pct,
       ROUND(AVG(avg_csat), 2) AS avg_csat, ROUND(AVG(reopen_pct), 2) AS avg_reopen_pct,
       STRING_AGG(DISTINCT experience_level, ', ') AS experience_levels
FROM q GROUP BY quartile ORDER BY quartile;
```

</details>

| quartile | agents | avg_sla_pct | avg_csat | avg_reopen_pct | experience_levels |
|---|---|---|---|---|---|
| 1 | 15 | 87.93 | 3.92 | 5.27 | Junior, Lead, Mid-Level, Senior |
| 2 | 15 | 78.45 | 3.89 | 5.98 | Lead, Mid-Level, Senior |
| 3 | 14 | 70.03 | 3.68 | 9.18 | Junior, Lead, Mid-Level |
| 4 | 14 | 51.27 | 3.49 | 13.92 | Junior, Mid-Level, Senior |

### Q07.01

**Operational KPIs overall**

* **Business question:** What are total transactions, success/failure rates, processing time and cost?
* **Techniques:** aggregate functions, weighted average
* **Result:** 1 rows in 6 ms

<details><summary>SQL</summary>

```sql
SELECT SUM(total_transactions) AS total_transactions,
       SUM(successful_transactions) AS successful,
       SUM(failed_transactions) AS failed,
       ROUND(100.0 * SUM(successful_transactions) / SUM(total_transactions), 2) AS success_rate_pct,
       ROUND(100.0 * SUM(failed_transactions) / SUM(total_transactions), 2) AS failure_rate_pct,
       ROUND(SUM(processing_time_minutes * total_transactions) / SUM(total_transactions), 2) AS avg_processing_min,
       ROUND(SUM(operational_cost), 2) AS total_cost,
       ROUND(SUM(operational_cost) / SUM(total_transactions), 4) AS cost_per_transaction
FROM support.operations;
```

</details>

| total_transactions | successful | failed | success_rate_pct | failure_rate_pct | avg_processing_min | total_cost | cost_per_transaction |
|---|---|---|---|---|---|---|---|
| 14979301 | 14679878 | 299423 | 98.00 | 2.00 | 2.77 | 11,944,594.04 | 0.80 |

### Q07.02

**Process performance ranked by failure rate**

* **Business question:** Which operational processes have the highest failure rates?
* **Techniques:** reporting view, ORDER BY
* **Result:** 13 rows in 12 ms

<details><summary>SQL</summary>

```sql
SELECT * FROM support.v_process_performance ORDER BY failure_rate_pct DESC;
```

</details>

| department_id | department_name | operation_type | process_name | transactions | success_rate_pct | failure_rate_pct | avg_processing_min | operational_cost | degraded_days_pct |
|---|---|---|---|---|---|---|---|---|---|
| DEP-02 | Billing & Accounts | Refund Processing | Refund Approval | 310326 | 91.22 | 8.78 | 9.68 | 920,254.68 | 89.42 |
| DEP-05 | Returns & Refunds | Returns Processing | Returns Inspection | 357714 | 95.79 | 4.21 | 16.13 | 1,304,657.52 | 23.54 |
| DEP-02 | Billing & Accounts | Payment Processing | Payment Reconciliation | 1310492 | 96.06 | 3.94 | 2.24 | 969,303.60 | 17.70 |
| DEP-06 | Customer Success | Customer Onboarding | Onboarding Setup | 142715 | 97.38 | 2.62 | 25.26 | 1,112,226.63 | 7.21 |
| DEP-04 | Logistics & Delivery | Fulfillment | Shipment Dispatch | 2024343 | 97.73 | 2.27 | 4.52 | 2,484,451.11 | 0.55 |
| DEP-05 | Returns & Refunds | Returns Processing | Restocking | 333371 | 97.90 | 2.10 | 6.06 | 591,659.50 | 1.28 |

### Q07.03

**Operational cost by department**

* **Business question:** Which departments have the highest operational (transaction) costs?
* **Techniques:** INNER JOIN, GROUP BY, share of total via window
* **Result:** 6 rows in 7 ms

<details><summary>SQL</summary>

```sql
SELECT d.department_name, SUM(o.total_transactions) AS transactions, ROUND(SUM(o.operational_cost), 0) AS operational_cost,
       ROUND(100.0 * SUM(o.operational_cost) / SUM(SUM(o.operational_cost)) OVER (), 2) AS share_of_cost_pct
FROM support.operations o JOIN support.departments d USING (department_id)
GROUP BY d.department_name
ORDER BY operational_cost DESC;
```

</details>

| department_name | transactions | operational_cost | share_of_cost_pct |
|---|---|---|---|
| Logistics & Delivery | 3929433 | 3,580,077.00 | 29.97 |
| Billing & Accounts | 3408581 | 2,361,921.00 | 19.77 |
| Returns & Refunds | 691085 | 1,896,317.00 | 15.88 |
| Customer Success | 249601 | 1,715,624.00 | 14.36 |
| Order Management | 5127312 | 1,491,223.00 | 12.48 |
| Technical Support | 1573289 | 899,432.00 | 7.53 |

### Q07.04

**Days in degraded or critical state by process and year**

* **Business question:** Are operational incidents becoming more frequent?
* **Techniques:** conditional aggregation, EXTRACT(YEAR)
* **Result:** 10 rows in 5 ms

<details><summary>SQL</summary>

```sql
SELECT process_name,
       COUNT(*) FILTER (WHERE operational_status <> 'Normal' AND EXTRACT(YEAR FROM operation_date) = 2023) AS bad_days_2023,
       COUNT(*) FILTER (WHERE operational_status <> 'Normal' AND EXTRACT(YEAR FROM operation_date) = 2024) AS bad_days_2024,
       COUNT(*) FILTER (WHERE operational_status <> 'Normal' AND EXTRACT(YEAR FROM operation_date) = 2025) AS bad_days_2025
FROM support.operations
GROUP BY process_name
HAVING COUNT(*) FILTER (WHERE operational_status <> 'Normal') > 10
ORDER BY bad_days_2025 DESC;
```

</details>

| process_name | bad_days_2023 | bad_days_2024 | bad_days_2025 |
|---|---|---|---|
| Refund Approval | 283 | 341 | 356 |
| Payment Reconciliation | 8 | 8 | 178 |
| Returns Inspection | 84 | 99 | 75 |
| Onboarding Setup | 23 | 32 | 24 |
| Contract Renewal | 16 | 12 | 14 |
| Carrier Handoff | 7 | 3 | 6 |

### Q07.05

**Peak-season processing time**

* **Business question:** Which processes slow down in November-December?
* **Techniques:** subquery in FROM, FILTERed weighted averages, ratio
* **Result:** 13 rows in 13 ms

<details><summary>SQL</summary>

```sql
SELECT process_name, peak_min, offpeak_min, ROUND(100.0 * (peak_min / NULLIF(offpeak_min, 0) - 1), 1) AS peak_uplift_pct
FROM (
    SELECT process_name,
           ROUND(SUM(processing_time_minutes * total_transactions) FILTER (WHERE EXTRACT(MONTH FROM operation_date) IN (11,12))
                 / SUM(total_transactions) FILTER (WHERE EXTRACT(MONTH FROM operation_date) IN (11,12)), 2) AS peak_min,
           ROUND(SUM(processing_time_minutes * total_transactions) FILTER (WHERE EXTRACT(MONTH FROM operation_date) NOT IN (11,12))
                 / SUM(total_transactions) FILTER (WHERE EXTRACT(MONTH FROM operation_date) NOT IN (11,12)), 2) AS offpeak_min
    FROM support.operations
    GROUP BY process_name
) x
ORDER BY peak_uplift_pct DESC;
```

</details>

| process_name | peak_min | offpeak_min | peak_uplift_pct |
|---|---|---|---|
| Shipment Dispatch | 6.29 | 4.04 | 55.70 |
| Returns Inspection | 16.32 | 16.07 | 1.60 |
| Refund Approval | 9.76 | 9.66 | 1.00 |
| Order Entry | 1.44 | 1.43 | 0.70 |
| Onboarding Setup | 25.37 | 25.23 | 0.60 |
| Payment Reconciliation | 2.25 | 2.24 | 0.40 |

### Q07.06

**Departmental cost by category and year**

* **Business question:** Where is departmental spend going and how fast is each category growing?
* **Techniques:** conditional aggregation pivot, growth calculation
* **Result:** 6 rows in 2 ms

<details><summary>SQL</summary>

```sql
SELECT cost_category,
       ROUND(SUM(total_cost) FILTER (WHERE EXTRACT(YEAR FROM cost_date) = 2023), 0) AS cost_2023,
       ROUND(SUM(total_cost) FILTER (WHERE EXTRACT(YEAR FROM cost_date) = 2024), 0) AS cost_2024,
       ROUND(SUM(total_cost) FILTER (WHERE EXTRACT(YEAR FROM cost_date) = 2025), 0) AS cost_2025,
       ROUND(100.0 * (SUM(total_cost) FILTER (WHERE EXTRACT(YEAR FROM cost_date) = 2025)
                      / SUM(total_cost) FILTER (WHERE EXTRACT(YEAR FROM cost_date) = 2023) - 1), 1) AS growth_23_25_pct
FROM support.business_costs
GROUP BY cost_category
ORDER BY cost_2025 DESC;
```

</details>

| cost_category | cost_2023 | cost_2024 | cost_2025 | growth_23_25_pct |
|---|---|---|---|---|
| Personnel | 2,071,112.00 | 2,138,931.00 | 2,217,615.00 | 7.10 |
| Technology & Software | 495,646.00 | 512,108.00 | 539,764.00 | 8.90 |
| Outsourcing | 356,281.00 | 366,941.00 | 439,887.00 | 23.50 |
| Facilities | 280,936.00 | 295,912.00 | 304,854.00 | 8.50 |
| Telecommunications | 212,905.00 | 222,372.00 | 229,105.00 | 7.60 |
| Training & Development | 150,846.00 | 155,732.00 | 161,760.00 | 7.20 |

### Q07.07

**Spend vs budget by department and year**

* **Business question:** Which departments overspend their budget?
* **Techniques:** JOIN, GROUP BY, derived utilisation %
* **Result:** 18 rows in 3 ms

<details><summary>SQL</summary>

```sql
SELECT d.department_name, EXTRACT(YEAR FROM bc.cost_date)::int AS year,
       ROUND(SUM(bc.total_cost), 0) AS spend, d.operational_budget AS budget,
       ROUND(100.0 * SUM(bc.total_cost) / d.operational_budget, 1) AS utilisation_pct
FROM support.business_costs bc JOIN support.departments d USING (department_id)
GROUP BY d.department_name, EXTRACT(YEAR FROM bc.cost_date), d.operational_budget
ORDER BY year DESC, utilisation_pct DESC;
```

</details>

| department_name | year | spend | budget | utilisation_pct |
|---|---|---|---|---|
| Billing & Accounts | 2025 | 633,386.00 | 520,000.00 | 121.80 |
| Order Management | 2025 | 536,209.00 | 480,000.00 | 111.70 |
| Customer Success | 2025 | 615,634.00 | 560,000.00 | 109.90 |
| Technical Support | 2025 | 986,425.00 | 900,000.00 | 109.60 |
| Logistics & Delivery | 2025 | 707,751.00 | 650,000.00 | 108.90 |
| Returns & Refunds | 2025 | 413,580.00 | 380,000.00 | 108.80 |

### Q07.08

**Cost per resolved ticket by department and year**

* **Business question:** How much does it cost to resolve one ticket in each department?
* **Techniques:** two CTEs joined on department and year
* **Result:** 18 rows in 13 ms

<details><summary>SQL</summary>

```sql
WITH cost AS (
    SELECT department_id, EXTRACT(YEAR FROM cost_date)::int AS year, SUM(total_cost) AS total_cost
    FROM support.business_costs GROUP BY 1, 2
), resolved AS (
    SELECT department_id, EXTRACT(YEAR FROM ticket_created_date)::int AS year, COUNT(*) AS resolved
    FROM support.support_tickets WHERE ticket_status IN ('Closed','Resolved') GROUP BY 1, 2
)
SELECT d.department_name, c.year, r.resolved, ROUND(c.total_cost, 0) AS total_cost,
       ROUND(c.total_cost / NULLIF(r.resolved, 0), 2) AS cost_per_resolved_ticket
FROM cost c JOIN resolved r USING (department_id, year) JOIN support.departments d USING (department_id)
ORDER BY d.department_name, c.year;
```

</details>

| department_name | year | resolved | total_cost | cost_per_resolved_ticket |
|---|---|---|---|---|
| Billing & Accounts | 2023 | 1246 | 528,225.00 | 423.94 |
| Billing & Accounts | 2024 | 1449 | 547,453.00 | 377.81 |
| Billing & Accounts | 2025 | 2030 | 633,386.00 | 312.01 |
| Customer Success | 2023 | 735 | 567,146.00 | 771.63 |
| Customer Success | 2024 | 781 | 588,817.00 | 753.93 |
| Customer Success | 2025 | 760 | 615,634.00 | 810.04 |

### Q08.01

**Monthly tickets: running total, 3-month moving average, MoM %**

* **Business question:** How is ticket volume trending month over month?
* **Techniques:** CTE, SUM() OVER running total, AVG() OVER ROWS moving average, LAG
* **Result:** 36 rows in 21 ms

<details><summary>SQL</summary>

```sql
WITH m AS (SELECT created_month, tickets FROM support.v_monthly_support_kpis)
SELECT created_month, tickets,
       SUM(tickets) OVER (ORDER BY created_month)                                       AS running_total,
       ROUND(AVG(tickets) OVER (ORDER BY created_month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 1) AS moving_avg_3m,
       ROUND(100.0 * (tickets - LAG(tickets) OVER (ORDER BY created_month)) / LAG(tickets) OVER (ORDER BY created_month), 1) AS mom_pct
FROM m ORDER BY created_month;
```

</details>

| created_month | tickets | running_total | moving_avg_3m | mom_pct |
|---|---|---|---|---|
| 2023-01 | 631 | 631.00 | 631.00 |  |
| 2023-02 | 510 | 1,141.00 | 570.50 | -19.20 |
| 2023-03 | 571 | 1,712.00 | 570.70 | 12.00 |
| 2023-04 | 534 | 2,246.00 | 538.30 | -6.50 |
| 2023-05 | 600 | 2,846.00 | 568.30 | 12.40 |
| 2023-06 | 553 | 3,399.00 | 562.30 | -7.80 |

### Q08.02

**Year-over-year KPI comparison by month**

* **Business question:** How does each month compare with the same month last year?
* **Techniques:** LAG with offset 12, SUBSTRING on month key
* **Result:** 12 rows in 21 ms

<details><summary>SQL</summary>

```sql
WITH m AS (SELECT * FROM support.v_monthly_support_kpis)
SELECT created_month, tickets,
       LAG(tickets, 12) OVER (ORDER BY created_month) AS tickets_last_year,
       ROUND(100.0 * (tickets - LAG(tickets, 12) OVER (ORDER BY created_month)) / NULLIF(LAG(tickets, 12) OVER (ORDER BY created_month), 0), 1) AS yoy_pct,
       sla_compliance_pct,
       sla_compliance_pct - LAG(sla_compliance_pct, 12) OVER (ORDER BY created_month) AS sla_yoy_pp
FROM m
ORDER BY created_month DESC
LIMIT 12;
```

</details>

| created_month | tickets | tickets_last_year | yoy_pct | sla_compliance_pct | sla_yoy_pp |
|---|---|---|---|---|---|
| 2025-12 | 968 | 921 | 5.10 | 58.45 | -3.72 |
| 2025-11 | 881 | 831 | 6.00 | 56.17 | -10.66 |
| 2025-10 | 798 | 714 | 11.80 | 67.34 | -5.76 |
| 2025-09 | 693 | 663 | 4.50 | 69.50 | -5.07 |
| 2025-08 | 638 | 614 | 3.90 | 75.16 | -4.14 |
| 2025-07 | 624 | 560 | 11.40 | 76.67 | -4.76 |

### Q08.03

**SLA breach analysis by department, priority and year**

* **Business question:** Where are SLA breaches concentrated, and is it getting worse?
* **Techniques:** GROUP BY three dimensions, window comparison to department average
* **Result:** 15 rows in 17 ms

<details><summary>SQL</summary>

```sql
WITH s AS (
    SELECT department_name, ticket_priority, created_year,
           COUNT(*) FILTER (WHERE sla_eligible) AS resolved,
           COUNT(*) FILTER (WHERE sla_met = FALSE) AS breaches
    FROM support.v_ticket_metrics GROUP BY 1, 2, 3
)
SELECT department_name, ticket_priority, created_year, resolved, breaches,
       ROUND(100.0 * breaches / NULLIF(resolved, 0), 2) AS breach_pct,
       ROUND(100.0 * SUM(breaches) OVER (PARTITION BY department_name, created_year)
             / SUM(resolved) OVER (PARTITION BY department_name, created_year), 2) AS dept_year_breach_pct
FROM s
WHERE created_year = 2025
ORDER BY breach_pct DESC
LIMIT 15;
```

</details>

| department_name | ticket_priority | created_year | resolved | breaches | breach_pct | dept_year_breach_pct |
|---|---|---|---|---|---|---|
| Returns & Refunds | Critical | 2025 | 63 | 40 | 63.49 | 46.72 |
| Billing & Accounts | Critical | 2025 | 133 | 84 | 63.16 | 39.92 |
| Logistics & Delivery | Critical | 2025 | 51 | 31 | 60.78 | 38.64 |
| Returns & Refunds | Medium | 2025 | 383 | 183 | 47.78 | 46.72 |
| Returns & Refunds | High | 2025 | 195 | 91 | 46.67 | 46.72 |
| Logistics & Delivery | High | 2025 | 185 | 85 | 45.95 | 38.64 |

### Q08.04

**Departmental benchmarking against company average**

* **Business question:** How does each department compare with the company on the core KPIs?
* **Techniques:** CTE, CROSS JOIN to company-level totals, differences in percentage points
* **Result:** 6 rows in 49 ms

<details><summary>SQL</summary>

```sql
WITH d AS (
    SELECT department_name,
           ROUND((AVG(resolution_hours) FILTER (WHERE sla_eligible))::numeric, 2) AS avg_res_h,
           ROUND(100.0 * COUNT(*) FILTER (WHERE sla_met) / COUNT(*) FILTER (WHERE sla_eligible), 2) AS sla_pct,
           ROUND(100.0 * COUNT(*) FILTER (WHERE is_fcr) / COUNT(*) FILTER (WHERE sla_eligible), 2) AS fcr_pct,
           ROUND(AVG(satisfaction_score)::numeric, 3) AS csat
    FROM support.v_ticket_metrics GROUP BY department_name
), c AS (
    SELECT avg_resolution_h AS c_res, sla_compliance_pct AS c_sla, fcr_rate_pct AS c_fcr, avg_csat AS c_csat
    FROM support.v_kpi_summary
)
SELECT d.department_name, d.avg_res_h, ROUND(d.avg_res_h - c.c_res, 2) AS res_vs_company_h,
       d.sla_pct, ROUND(d.sla_pct - c.c_sla, 2) AS sla_vs_company_pp,
       d.fcr_pct, ROUND(d.fcr_pct - c.c_fcr, 2) AS fcr_vs_company_pp,
       d.csat, ROUND(d.csat - c.c_csat, 3) AS csat_vs_company
FROM d CROSS JOIN c
ORDER BY sla_vs_company_pp;
```

</details>

| department_name | avg_res_h | res_vs_company_h | sla_pct | sla_vs_company_pp | fcr_pct | fcr_vs_company_pp | csat | csat_vs_company |
|---|---|---|---|---|---|---|---|---|
| Returns & Refunds | 59.75 | 25.29 | 50.00 | -22.91 | 10.63 | -10.86 | 3.55 | -0.20 |
| Logistics & Delivery | 43.39 | 8.93 | 63.85 | -9.06 | 14.23 | -7.26 | 3.61 | -0.14 |
| Billing & Accounts | 35.88 | 1.42 | 73.73 | 0.82 | 20.61 | -0.88 | 3.73 | -0.03 |
| Technical Support | 30.03 | -4.43 | 74.71 | 1.80 | 22.36 | 0.87 | 3.79 | 0.04 |
| Customer Success | 23.88 | -10.58 | 83.07 | 10.16 | 28.98 | 7.49 | 3.75 | 0.00 |
| Order Management | 20.80 | -13.66 | 88.22 | 15.31 | 31.28 | 9.79 | 4.00 | 0.25 |

### Q08.05

**Monthly backlog reconstruction**

* **Business question:** How many tickets were open at the end of each month (backlog trend)?
* **Techniques:** generate_series, correlated aggregation over a date spine
* **Result:** 12 rows in 169 ms

<details><summary>SQL</summary>

```sql
WITH months AS (
    SELECT (date_trunc('month', d) + INTERVAL '1 month' - INTERVAL '1 second')::timestamp AS month_end
    FROM generate_series(DATE '2023-01-01', DATE '2025-12-01', INTERVAL '1 month') d
)
SELECT TO_CHAR(m.month_end, 'YYYY-MM') AS month,
       COUNT(t.ticket_id) AS open_at_month_end
FROM months m
LEFT JOIN support.support_tickets t
       ON t.ticket_created_date <= m.month_end
      AND t.ticket_status <> 'Cancelled'
      AND (COALESCE(t.resolved_date, CASE WHEN t.resolution_ts_invalid THEN t.ticket_created_date END) IS NULL
           OR COALESCE(t.resolved_date, t.ticket_created_date) > m.month_end)
GROUP BY m.month_end
ORDER BY m.month_end DESC
LIMIT 12;
```

</details>

| month | open_at_month_end |
|---|---|
| 2025-12 | 257 |
| 2025-11 | 201 |
| 2025-10 | 148 |
| 2025-09 | 102 |
| 2025-08 | 55 |
| 2025-07 | 55 |

### Q08.06

**Repeat contact analysis (7-day window)**

* **Business question:** Which categories cause customers to come back within a week?
* **Techniques:** LAG over customer partition (in view), LEAD to find next category
* **Result:** 8 rows in 32 ms

<details><summary>SQL</summary>

```sql
WITH seq AS (
    SELECT customer_id, ticket_category, ticket_created_date,
           LEAD(ticket_category)     OVER (PARTITION BY customer_id ORDER BY ticket_created_date) AS next_category,
           LEAD(ticket_created_date) OVER (PARTITION BY customer_id ORDER BY ticket_created_date) AS next_created
    FROM support.support_tickets
)
SELECT ticket_category,
       COUNT(*) AS tickets,
       COUNT(*) FILTER (WHERE next_created - ticket_created_date <= INTERVAL '7 days') AS followed_within_7d,
       ROUND(100.0 * COUNT(*) FILTER (WHERE next_created - ticket_created_date <= INTERVAL '7 days') / COUNT(*), 2) AS repeat_7d_pct,
       ROUND(100.0 * COUNT(*) FILTER (WHERE next_created - ticket_created_date <= INTERVAL '7 days' AND next_category = ticket_category)
             / NULLIF(COUNT(*) FILTER (WHERE next_created - ticket_created_date <= INTERVAL '7 days'), 0), 2) AS same_category_pct
FROM seq
GROUP BY ticket_category
ORDER BY repeat_7d_pct DESC;
```

</details>

| ticket_category | tickets | followed_within_7d | repeat_7d_pct | same_category_pct |
|---|---|---|---|---|
| Order Status | 3084 | 525 | 17.02 | 10.86 |
| Returns & Refunds | 2832 | 475 | 16.77 | 11.79 |
| Account Access | 2578 | 413 | 16.02 | 10.90 |
| Product Inquiry | 1368 | 217 | 15.86 | 5.53 |
| Billing & Payment | 4885 | 768 | 15.72 | 22.01 |
| Complaint | 976 | 153 | 15.68 | 4.58 |

### Q08.07

**Customer value x experience segmentation**

* **Business question:** Which high-value customers have poor support experiences (retention risk)?
* **Techniques:** NTILE for value tiers, CASE segmentation matrix
* **Result:** 9 rows in 28 ms

<details><summary>SQL</summary>

```sql
WITH c AS (
    SELECT *, NTILE(3) OVER (ORDER BY customer_lifetime_value DESC) AS value_tier
    FROM support.v_customer_360 WHERE tickets > 0 AND avg_csat IS NOT NULL
)
SELECT CASE value_tier WHEN 1 THEN 'High value' WHEN 2 THEN 'Mid value' ELSE 'Low value' END AS value_tier,
       CASE WHEN avg_csat >= 4 THEN 'Satisfied' WHEN avg_csat >= 3 THEN 'Neutral' ELSE 'At risk' END AS experience,
       COUNT(*) AS customers, ROUND(SUM(customer_lifetime_value), 0) AS clv_at_stake,
       COUNT(*) FILTER (WHERE customer_status = 'Churned') AS churned
FROM c
GROUP BY 1, 2, value_tier
ORDER BY value_tier, experience;
```

</details>

| value_tier | experience | customers | clv_at_stake | churned |
|---|---|---|---|---|
| High value | At risk | 32 | 1,190,876.00 | 6 |
| High value | Neutral | 423 | 14,470,707.00 | 54 |
| High value | Satisfied | 289 | 8,629,567.00 | 22 |
| Low value | At risk | 56 | 46,639.00 | 9 |
| Low value | Neutral | 311 | 277,357.00 | 38 |
| Low value | Satisfied | 376 | 335,699.00 | 26 |

### Q08.08

**Payment Reconciliation before vs after April 2025**

* **Business question:** Did the April 2025 change coincide with a jump in failures and Billing tickets?
* **Techniques:** UNION of two aggregates, date filters
* **Result:** 2 rows in 6 ms

<details><summary>SQL</summary>

```sql
SELECT 'Payment Reconciliation failure %' AS metric,
       ROUND(100.0 * SUM(failed_transactions) FILTER (WHERE operation_date <  DATE '2025-04-01') / SUM(total_transactions) FILTER (WHERE operation_date <  DATE '2025-04-01'), 2) AS before_apr_2025,
       ROUND(100.0 * SUM(failed_transactions) FILTER (WHERE operation_date >= DATE '2025-04-01') / SUM(total_transactions) FILTER (WHERE operation_date >= DATE '2025-04-01'), 2) AS after_apr_2025
FROM support.operations WHERE process_name = 'Payment Reconciliation'
UNION ALL
SELECT 'Billing & Payment share of tickets %',
       ROUND(100.0 * COUNT(*) FILTER (WHERE ticket_category = 'Billing & Payment' AND ticket_created_date <  DATE '2025-04-01') / COUNT(*) FILTER (WHERE ticket_created_date <  DATE '2025-04-01'), 2),
       ROUND(100.0 * COUNT(*) FILTER (WHERE ticket_category = 'Billing & Payment' AND ticket_created_date >= DATE '2025-04-01') / COUNT(*) FILTER (WHERE ticket_created_date >= DATE '2025-04-01'), 2)
FROM support.support_tickets;
```

</details>

| metric | before_apr_2025 | after_apr_2025 |
|---|---|---|
| Payment Reconciliation failure % | 3.18 | 5.90 |
| Billing & Payment share of tickets % | 17.93 | 26.64 |

### Q08.09

**Cost efficiency trend: cost per transaction, 3-month moving average**

* **Business question:** Is unit cost rising faster than volume?
* **Techniques:** aggregation by month, AVG() OVER ROWS window, FIRST_VALUE for index
* **Result:** 12 rows in 18 ms

<details><summary>SQL</summary>

```sql
WITH m AS (
    SELECT TO_CHAR(operation_date, 'YYYY-MM') AS month, SUM(operational_cost) AS cost, SUM(total_transactions) AS txns
    FROM support.operations GROUP BY 1
)
SELECT month, txns, ROUND(cost, 0) AS cost, ROUND(cost / txns, 4) AS cost_per_txn,
       ROUND(AVG(cost / txns) OVER (ORDER BY month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 4) AS cpt_ma3,
       ROUND(100.0 * (cost / txns) / FIRST_VALUE(cost / txns) OVER (ORDER BY month), 1) AS cpt_index_jan23_100
FROM m ORDER BY month DESC LIMIT 12;
```

</details>

| month | txns | cost | cost_per_txn | cpt_ma3 | cpt_index_jan23_100 |
|---|---|---|---|---|---|
| 2025-12 | 597832 | 476,032.00 | 0.80 | 0.80 | 102.00 |
| 2025-11 | 548312 | 437,124.00 | 0.80 | 0.81 | 102.10 |
| 2025-10 | 451155 | 369,821.00 | 0.82 | 0.82 | 105.00 |
| 2025-09 | 434415 | 358,564.00 | 0.83 | 0.82 | 105.70 |
| 2025-08 | 428231 | 353,255.00 | 0.82 | 0.82 | 105.70 |
| 2025-07 | 444193 | 362,624.00 | 0.82 | 0.82 | 104.60 |

### Q08.10

**Agent percentile ranking (PERCENT_RANK, CUME_DIST)**

* **Business question:** Where does each agent sit in the company distribution of CSAT?
* **Techniques:** PERCENT_RANK, CUME_DIST
* **Result:** 10 rows in 25 ms

<details><summary>SQL</summary>

```sql
SELECT agent_name, department_name, avg_csat,
       ROUND(PERCENT_RANK() OVER (ORDER BY avg_csat)::numeric, 3) AS pct_rank,
       ROUND(CUME_DIST()    OVER (ORDER BY avg_csat)::numeric, 3) AS cume_dist
FROM support.v_agent_scorecard
WHERE avg_csat IS NOT NULL
ORDER BY avg_csat
LIMIT 10;
```

</details>

| agent_name | department_name | avg_csat | pct_rank | cume_dist |
|---|---|---|---|---|
| Eric Carney | Returns & Refunds | 3.21 | 0.00 | 0.02 |
| Shane Henderson | Logistics & Delivery | 3.24 | 0.02 | 0.03 |
| Fred Smith | Logistics & Delivery | 3.33 | 0.03 | 0.05 |
| Donald Wright | Customer Success | 3.33 | 0.05 | 0.07 |
| Jessica Holmes | Returns & Refunds | 3.38 | 0.07 | 0.08 |
| Anthony Rodriguez | Billing & Accounts | 3.44 | 0.09 | 0.10 |

### Q08.11

**Headline KPI summary (matches Python KPI engine)**

* **Business question:** What are the headline support and operations KPIs?
* **Techniques:** reporting view
* **Result:** 1 rows in 97 ms

<details><summary>SQL</summary>

```sql
SELECT * FROM support.v_kpi_summary;
```

</details>

| total_tickets | open_tickets | closed_tickets | pending_tickets | escalated_tickets | reopened_tickets | avg_first_response_h | median_first_response_h | avg_resolution_h | fcr_rate_pct | resolution_rate_pct | sla_compliance_pct | sla_breach_pct | avg_csat | csat_rate_pct | tickets_per_agent | repeat_contact_pct | total_transactions | successful_transactions | failed_transactions | operational_success_pct | operational_failure_pct | avg_processing_min | total_operational_cost | cost_per_transaction | cost_per_resolved_ticket |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 24000 | 257 | 23236 | 89 | 2403 | 1932 | 5.76 | 1.14 | 34.46 | 21.49 | 98.91 | 72.91 | 27.09 | 3.75 | 63.36 | 399.80 | 15.97 | 14979301 | 14679878 | 299423 | 98.00 | 2.00 | 2.77 | 11,944,594.04 | 0.80 | 479.98 |

-- =============================================================================
-- 08_advanced_analytics / advanced_analytics.sql
-- =============================================================================

-- @query Q08.01
-- @title Monthly tickets: running total, 3-month moving average, MoM %
-- @question How is ticket volume trending month over month?
-- @techniques CTE, SUM() OVER running total, AVG() OVER ROWS moving average, LAG
WITH m AS (SELECT created_month, tickets FROM support.v_monthly_support_kpis)
SELECT created_month, tickets,
       SUM(tickets) OVER (ORDER BY created_month)                                       AS running_total,
       ROUND(AVG(tickets) OVER (ORDER BY created_month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 1) AS moving_avg_3m,
       ROUND(100.0 * (tickets - LAG(tickets) OVER (ORDER BY created_month)) / LAG(tickets) OVER (ORDER BY created_month), 1) AS mom_pct
FROM m ORDER BY created_month;

-- @query Q08.02
-- @title Year-over-year KPI comparison by month
-- @question How does each month compare with the same month last year?
-- @techniques LAG with offset 12, SUBSTRING on month key
WITH m AS (SELECT * FROM support.v_monthly_support_kpis)
SELECT created_month, tickets,
       LAG(tickets, 12) OVER (ORDER BY created_month) AS tickets_last_year,
       ROUND(100.0 * (tickets - LAG(tickets, 12) OVER (ORDER BY created_month)) / NULLIF(LAG(tickets, 12) OVER (ORDER BY created_month), 0), 1) AS yoy_pct,
       sla_compliance_pct,
       sla_compliance_pct - LAG(sla_compliance_pct, 12) OVER (ORDER BY created_month) AS sla_yoy_pp
FROM m
ORDER BY created_month DESC
LIMIT 12;

-- @query Q08.03
-- @title SLA breach analysis by department, priority and year
-- @question Where are SLA breaches concentrated, and is it getting worse?
-- @techniques GROUP BY three dimensions, window comparison to department average
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

-- @query Q08.04
-- @title Departmental benchmarking against company average
-- @question How does each department compare with the company on the core KPIs?
-- @techniques CTE, CROSS JOIN to company-level totals, differences in percentage points
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

-- @query Q08.05
-- @title Monthly backlog reconstruction
-- @question How many tickets were open at the end of each month (backlog trend)?
-- @techniques generate_series, correlated aggregation over a date spine
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

-- @query Q08.06
-- @title Repeat contact analysis (7-day window)
-- @question Which categories cause customers to come back within a week?
-- @techniques LAG over customer partition (in view), LEAD to find next category
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

-- @query Q08.07
-- @title Customer value x experience segmentation
-- @question Which high-value customers have poor support experiences (retention risk)?
-- @techniques NTILE for value tiers, CASE segmentation matrix
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

-- @query Q08.08
-- @title Payment Reconciliation before vs after April 2025
-- @question Did the April 2025 change coincide with a jump in failures and Billing tickets?
-- @techniques UNION of two aggregates, date filters
SELECT 'Payment Reconciliation failure %' AS metric,
       ROUND(100.0 * SUM(failed_transactions) FILTER (WHERE operation_date <  DATE '2025-04-01') / SUM(total_transactions) FILTER (WHERE operation_date <  DATE '2025-04-01'), 2) AS before_apr_2025,
       ROUND(100.0 * SUM(failed_transactions) FILTER (WHERE operation_date >= DATE '2025-04-01') / SUM(total_transactions) FILTER (WHERE operation_date >= DATE '2025-04-01'), 2) AS after_apr_2025
FROM support.operations WHERE process_name = 'Payment Reconciliation'
UNION ALL
SELECT 'Billing & Payment share of tickets %',
       ROUND(100.0 * COUNT(*) FILTER (WHERE ticket_category = 'Billing & Payment' AND ticket_created_date <  DATE '2025-04-01') / COUNT(*) FILTER (WHERE ticket_created_date <  DATE '2025-04-01'), 2),
       ROUND(100.0 * COUNT(*) FILTER (WHERE ticket_category = 'Billing & Payment' AND ticket_created_date >= DATE '2025-04-01') / COUNT(*) FILTER (WHERE ticket_created_date >= DATE '2025-04-01'), 2)
FROM support.support_tickets;

-- @query Q08.09
-- @title Cost efficiency trend: cost per transaction, 3-month moving average
-- @question Is unit cost rising faster than volume?
-- @techniques aggregation by month, AVG() OVER ROWS window, FIRST_VALUE for index
WITH m AS (
    SELECT TO_CHAR(operation_date, 'YYYY-MM') AS month, SUM(operational_cost) AS cost, SUM(total_transactions) AS txns
    FROM support.operations GROUP BY 1
)
SELECT month, txns, ROUND(cost, 0) AS cost, ROUND(cost / txns, 4) AS cost_per_txn,
       ROUND(AVG(cost / txns) OVER (ORDER BY month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 4) AS cpt_ma3,
       ROUND(100.0 * (cost / txns) / FIRST_VALUE(cost / txns) OVER (ORDER BY month), 1) AS cpt_index_jan23_100
FROM m ORDER BY month DESC LIMIT 12;

-- @query Q08.10
-- @title Agent percentile ranking (PERCENT_RANK, CUME_DIST)
-- @question Where does each agent sit in the company distribution of CSAT?
-- @techniques PERCENT_RANK, CUME_DIST
SELECT agent_name, department_name, avg_csat,
       ROUND(PERCENT_RANK() OVER (ORDER BY avg_csat)::numeric, 3) AS pct_rank,
       ROUND(CUME_DIST()    OVER (ORDER BY avg_csat)::numeric, 3) AS cume_dist
FROM support.v_agent_scorecard
WHERE avg_csat IS NOT NULL
ORDER BY avg_csat
LIMIT 10;

-- @query Q08.11
-- @title Headline KPI summary (matches Python KPI engine)
-- @question What are the headline support and operations KPIs?
-- @techniques reporting view
SELECT * FROM support.v_kpi_summary;

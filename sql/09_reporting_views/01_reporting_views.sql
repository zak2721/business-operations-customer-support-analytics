-- =============================================================================
-- 09_reporting_views / 01_reporting_views.sql
-- Reusable reporting layer. KPI definitions here are identical to the Python
-- KPI engine (src/kpi/kpis.py) and the DAX measures (powerbi/dax_measures.dax);
-- tests/test_sql.py asserts that SQL and Python produce the same numbers.
-- Snapshot ("as of") time for backlog/aging: 2025-12-31 23:59:59.
-- =============================================================================
SET search_path TO support;

-- ---------------------------------------------------------------------------
-- v_ticket_metrics : one row per ticket with all derived measures and flags
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_ticket_metrics AS
WITH base AS (
    SELECT t.*,
           EXTRACT(EPOCH FROM (t.first_response_date - t.ticket_created_date)) / 3600.0 AS first_response_hours,
           EXTRACT(EPOCH FROM (t.resolved_date       - t.ticket_created_date)) / 3600.0 AS resolution_hours,
           t.ticket_status IN ('Closed', 'Resolved')                AS is_resolved,
           t.ticket_status IN ('Open', 'In Progress', 'Pending')    AS is_unresolved,
           t.ticket_status = 'Cancelled'                            AS is_cancelled,
           LAG(t.ticket_created_date) OVER (PARTITION BY t.customer_id ORDER BY t.ticket_created_date) AS prev_ticket_created
    FROM support_tickets t
)
SELECT b.ticket_id, b.customer_id, b.agent_id, b.department_id, d.department_name,
       b.ticket_created_date, b.first_response_date, b.resolved_date,
       b.ticket_created_date::date                          AS created_date,
       TO_CHAR(b.ticket_created_date, 'YYYY-MM')            AS created_month,
       EXTRACT(YEAR FROM b.ticket_created_date)::int        AS created_year,
       b.ticket_category, b.ticket_subcategory, b.ticket_priority, b.ticket_status, b.support_channel,
       b.resolution_type, b.reopened_count, b.escalation_flag, b.sla_target_hours,
       b.first_response_hours, b.resolution_hours,
       b.is_resolved, b.is_unresolved, b.is_cancelled,
       (b.is_resolved AND b.resolved_date IS NOT NULL)                                       AS sla_eligible,
       CASE WHEN b.is_resolved AND b.resolved_date IS NOT NULL
            THEN b.resolution_hours <= b.sla_target_hours END                                AS sla_met,
       (b.is_resolved AND b.resolved_date IS NOT NULL AND b.resolution_type = 'First Contact Resolution'
            AND b.reopened_count = 0 AND b.escalation_flag = 0)                              AS is_fcr,
       b.reopened_count > 0                                                                  AS is_reopened,
       b.escalation_flag = 1                                                                 AS is_escalated,
       COALESCE(b.ticket_created_date - b.prev_ticket_created <= INTERVAL '7 days', FALSE)  AS is_repeat_contact,
       CASE WHEN b.is_unresolved
            THEN EXTRACT(EPOCH FROM (TIMESTAMP '2025-12-31 23:59:59' - b.ticket_created_date)) / 86400.0 END AS ticket_age_days,
       a.agent_name, a.experience_level, a.team,
       c.customer_segment, c.customer_region,
       f.satisfaction_score, f.customer_rating
FROM base b
JOIN departments d          ON d.department_id = b.department_id
LEFT JOIN agents a          ON a.agent_id = b.agent_id
JOIN customers c            ON c.customer_id = b.customer_id
LEFT JOIN customer_feedback f ON f.ticket_id = b.ticket_id;   -- UNIQUE(ticket_id) => no row multiplication

-- ---------------------------------------------------------------------------
-- v_kpi_summary : headline KPIs (single row)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_kpi_summary AS
WITH t AS (SELECT * FROM v_ticket_metrics),
     o AS (SELECT SUM(total_transactions) AS txns, SUM(successful_transactions) AS ok, SUM(failed_transactions) AS failed,
                  SUM(operational_cost) AS cost, SUM(processing_time_minutes * total_transactions) AS proc_min
           FROM operations),
     bc AS (SELECT SUM(total_cost) AS dept_cost FROM business_costs)
SELECT
    COUNT(*)                                                                   AS total_tickets,
    COUNT(*) FILTER (WHERE is_unresolved)                                      AS open_tickets,
    COUNT(*) FILTER (WHERE is_resolved)                                        AS closed_tickets,
    COUNT(*) FILTER (WHERE ticket_status = 'Pending')                          AS pending_tickets,
    COUNT(*) FILTER (WHERE is_escalated)                                       AS escalated_tickets,
    COUNT(*) FILTER (WHERE is_reopened)                                        AS reopened_tickets,
    ROUND(AVG(first_response_hours)::numeric, 2)                               AS avg_first_response_h,
    ROUND((PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY first_response_hours))::numeric, 2) AS median_first_response_h,
    ROUND((AVG(resolution_hours) FILTER (WHERE sla_eligible))::numeric, 2)     AS avg_resolution_h,
    ROUND(100.0 * COUNT(*) FILTER (WHERE is_fcr) / NULLIF(COUNT(*) FILTER (WHERE sla_eligible), 0), 2) AS fcr_rate_pct,
    ROUND(100.0 * COUNT(*) FILTER (WHERE is_resolved) / NULLIF(COUNT(*) FILTER (WHERE NOT is_cancelled), 0), 2) AS resolution_rate_pct,
    ROUND(100.0 * COUNT(*) FILTER (WHERE sla_met) / NULLIF(COUNT(*) FILTER (WHERE sla_eligible), 0), 2) AS sla_compliance_pct,
    ROUND(100.0 * COUNT(*) FILTER (WHERE sla_met = FALSE) / NULLIF(COUNT(*) FILTER (WHERE sla_eligible), 0), 2) AS sla_breach_pct,
    ROUND(AVG(satisfaction_score)::numeric, 3)                                 AS avg_csat,
    ROUND(100.0 * COUNT(*) FILTER (WHERE satisfaction_score >= 4) / NULLIF(COUNT(satisfaction_score), 0), 2) AS csat_rate_pct,
    ROUND(COUNT(agent_id)::numeric / NULLIF(COUNT(DISTINCT agent_id), 0), 1)  AS tickets_per_agent,
    ROUND(100.0 * COUNT(*) FILTER (WHERE is_repeat_contact) / COUNT(*), 2)     AS repeat_contact_pct,
    (SELECT txns FROM o)                                                       AS total_transactions,
    (SELECT ok FROM o)                                                         AS successful_transactions,
    (SELECT failed FROM o)                                                     AS failed_transactions,
    ROUND(100.0 * (SELECT ok FROM o) / (SELECT txns FROM o), 2)                AS operational_success_pct,
    ROUND(100.0 * (SELECT failed FROM o) / (SELECT txns FROM o), 2)            AS operational_failure_pct,
    ROUND((SELECT proc_min FROM o) / (SELECT txns FROM o), 2)                  AS avg_processing_min,
    ROUND((SELECT cost FROM o), 2)                                             AS total_operational_cost,
    ROUND((SELECT cost FROM o) / (SELECT txns FROM o), 4)                      AS cost_per_transaction,
    ROUND((SELECT dept_cost FROM bc) / NULLIF(COUNT(*) FILTER (WHERE is_resolved), 0), 2) AS cost_per_resolved_ticket
FROM t;

-- ---------------------------------------------------------------------------
-- v_monthly_support_kpis
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_monthly_support_kpis AS
SELECT created_month,
       COUNT(*)                                                                          AS tickets,
       ROUND(AVG(first_response_hours)::numeric, 2)                                      AS avg_frt_h,
       ROUND((AVG(resolution_hours) FILTER (WHERE sla_eligible))::numeric, 2)            AS avg_resolution_h,
       ROUND(100.0 * COUNT(*) FILTER (WHERE sla_met) / NULLIF(COUNT(*) FILTER (WHERE sla_eligible), 0), 2) AS sla_compliance_pct,
       ROUND(100.0 * COUNT(*) FILTER (WHERE is_fcr) / NULLIF(COUNT(*) FILTER (WHERE sla_eligible), 0), 2)  AS fcr_pct,
       ROUND(AVG(satisfaction_score)::numeric, 3)                                         AS avg_csat
FROM v_ticket_metrics
GROUP BY created_month;

-- ---------------------------------------------------------------------------
-- v_department_sla
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_department_sla AS
SELECT department_name, created_year,
       COUNT(*) FILTER (WHERE sla_eligible)                                               AS resolved_eligible,
       COUNT(*) FILTER (WHERE sla_met)                                                    AS within_sla,
       COUNT(*) FILTER (WHERE sla_met = FALSE)                                            AS breached,
       ROUND(100.0 * COUNT(*) FILTER (WHERE sla_met) / NULLIF(COUNT(*) FILTER (WHERE sla_eligible), 0), 2) AS sla_compliance_pct
FROM v_ticket_metrics
GROUP BY department_name, created_year;

-- ---------------------------------------------------------------------------
-- v_agent_scorecard
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_agent_scorecard AS
SELECT a.agent_id, a.agent_name, a.team, a.experience_level, a.employment_status, d.department_name,
       COUNT(t.ticket_id)                                                                 AS tickets_assigned,
       COUNT(*) FILTER (WHERE t.is_resolved)                                              AS tickets_resolved,
       ROUND(100.0 * COUNT(*) FILTER (WHERE t.is_resolved) / NULLIF(COUNT(*) FILTER (WHERE NOT t.is_cancelled), 0), 2) AS productivity_pct,
       ROUND((AVG(t.resolution_hours) FILTER (WHERE t.sla_eligible))::numeric, 2)         AS avg_resolution_h,
       ROUND(100.0 * COUNT(*) FILTER (WHERE t.sla_met) / NULLIF(COUNT(*) FILTER (WHERE t.sla_eligible), 0), 2) AS sla_compliance_pct,
       ROUND(100.0 * COUNT(*) FILTER (WHERE t.is_reopened) / NULLIF(COUNT(*) FILTER (WHERE t.is_resolved), 0), 2) AS reopen_pct,
       ROUND(AVG(t.satisfaction_score)::numeric, 3)                                        AS avg_csat
FROM agents a
JOIN departments d ON d.department_id = a.department_id
LEFT JOIN v_ticket_metrics t ON t.agent_id = a.agent_id
GROUP BY a.agent_id, a.agent_name, a.team, a.experience_level, a.employment_status, d.department_name;

-- ---------------------------------------------------------------------------
-- v_channel_performance
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_channel_performance AS
SELECT support_channel,
       COUNT(*)                                                                          AS tickets,
       ROUND(AVG(first_response_hours)::numeric, 2)                                      AS avg_frt_h,
       ROUND((AVG(resolution_hours) FILTER (WHERE sla_eligible))::numeric, 2)            AS avg_resolution_h,
       ROUND(100.0 * COUNT(*) FILTER (WHERE sla_met) / NULLIF(COUNT(*) FILTER (WHERE sla_eligible), 0), 2) AS sla_compliance_pct,
       ROUND(100.0 * COUNT(*) FILTER (WHERE is_fcr) / NULLIF(COUNT(*) FILTER (WHERE sla_eligible), 0), 2)  AS fcr_pct,
       ROUND(AVG(satisfaction_score)::numeric, 3)                                         AS avg_csat
FROM v_ticket_metrics
GROUP BY support_channel;

-- ---------------------------------------------------------------------------
-- v_backlog_aging
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_backlog_aging AS
SELECT CASE WHEN ticket_age_days <= 2  THEN '1. 0-2 days'
            WHEN ticket_age_days <= 7  THEN '2. 3-7 days'
            WHEN ticket_age_days <= 14 THEN '3. 8-14 days'
            WHEN ticket_age_days <= 30 THEN '4. 15-30 days'
            WHEN ticket_age_days <= 60 THEN '5. 31-60 days'
            ELSE '6. 60+ days' END                                  AS aging_bucket,
       COUNT(*)                                                     AS open_tickets,
       COUNT(*) FILTER (WHERE ticket_status = 'Open')               AS never_responded,
       COUNT(*) FILTER (WHERE ticket_age_days * 24 > sla_target_hours) AS past_sla_target
FROM v_ticket_metrics
WHERE is_unresolved
GROUP BY 1;

-- ---------------------------------------------------------------------------
-- v_operations_monthly / v_process_performance
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_operations_monthly AS
SELECT TO_CHAR(operation_date, 'YYYY-MM') AS month, department_id, process_name,
       SUM(total_transactions) AS transactions, SUM(successful_transactions) AS successful,
       SUM(failed_transactions) AS failed,
       ROUND(100.0 * SUM(failed_transactions) / NULLIF(SUM(total_transactions), 0), 3) AS failure_rate_pct,
       ROUND(SUM(processing_time_minutes * total_transactions) / NULLIF(SUM(total_transactions), 0), 2) AS avg_processing_min,
       ROUND(SUM(operational_cost), 2) AS operational_cost,
       ROUND(SUM(operational_cost) / NULLIF(SUM(total_transactions), 0), 4) AS cost_per_transaction
FROM operations
GROUP BY 1, 2, 3;

CREATE OR REPLACE VIEW v_process_performance AS
SELECT o.department_id, d.department_name, o.operation_type, o.process_name,
       SUM(o.total_transactions) AS transactions,
       ROUND(100.0 * SUM(o.successful_transactions) / SUM(o.total_transactions), 3) AS success_rate_pct,
       ROUND(100.0 * SUM(o.failed_transactions) / SUM(o.total_transactions), 3) AS failure_rate_pct,
       ROUND(SUM(o.processing_time_minutes * o.total_transactions) / SUM(o.total_transactions), 2) AS avg_processing_min,
       ROUND(SUM(o.operational_cost), 2) AS operational_cost,
       ROUND(100.0 * COUNT(*) FILTER (WHERE o.operational_status <> 'Normal') / COUNT(*), 2) AS degraded_days_pct
FROM operations o JOIN departments d USING (department_id)
GROUP BY o.department_id, d.department_name, o.operation_type, o.process_name;

-- ---------------------------------------------------------------------------
-- v_cost_by_department_month
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_cost_by_department_month AS
SELECT d.department_name, bc.cost_date, TO_CHAR(bc.cost_date, 'YYYY-MM') AS month,
       SUM(bc.direct_cost) AS direct_cost, SUM(bc.indirect_cost) AS indirect_cost, SUM(bc.total_cost) AS total_cost,
       d.operational_budget / 12.0 AS monthly_budget
FROM business_costs bc JOIN departments d USING (department_id)
GROUP BY d.department_name, bc.cost_date, d.operational_budget;

-- ---------------------------------------------------------------------------
-- v_customer_360 : customer-level support profile (no contact details exposed)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_customer_360 AS
SELECT c.customer_id, c.customer_segment, c.customer_region, c.customer_status, c.customer_lifetime_value,
       COUNT(t.ticket_id)                                   AS tickets,
       COUNT(*) FILTER (WHERE t.is_repeat_contact)          AS repeat_contacts,
       COUNT(*) FILTER (WHERE t.is_escalated)               AS escalations,
       ROUND(AVG(t.satisfaction_score)::numeric, 2)         AS avg_csat,
       MAX(t.ticket_created_date)                           AS last_contact
FROM customers c
LEFT JOIN v_ticket_metrics t ON t.customer_id = c.customer_id
GROUP BY c.customer_id, c.customer_segment, c.customer_region, c.customer_status, c.customer_lifetime_value;

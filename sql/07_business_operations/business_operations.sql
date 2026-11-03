-- =============================================================================
-- 07_business_operations / business_operations.sql
-- =============================================================================

-- @query Q07.01
-- @title Operational KPIs overall
-- @question What are total transactions, success/failure rates, processing time and cost?
-- @techniques aggregate functions, weighted average
SELECT SUM(total_transactions) AS total_transactions,
       SUM(successful_transactions) AS successful,
       SUM(failed_transactions) AS failed,
       ROUND(100.0 * SUM(successful_transactions) / SUM(total_transactions), 2) AS success_rate_pct,
       ROUND(100.0 * SUM(failed_transactions) / SUM(total_transactions), 2) AS failure_rate_pct,
       ROUND(SUM(processing_time_minutes * total_transactions) / SUM(total_transactions), 2) AS avg_processing_min,
       ROUND(SUM(operational_cost), 2) AS total_cost,
       ROUND(SUM(operational_cost) / SUM(total_transactions), 4) AS cost_per_transaction
FROM support.operations;

-- @query Q07.02
-- @title Process performance ranked by failure rate
-- @question Which operational processes have the highest failure rates?
-- @techniques reporting view, ORDER BY
SELECT * FROM support.v_process_performance ORDER BY failure_rate_pct DESC;

-- @query Q07.03
-- @title Operational cost by department
-- @question Which departments have the highest operational (transaction) costs?
-- @techniques INNER JOIN, GROUP BY, share of total via window
SELECT d.department_name, SUM(o.total_transactions) AS transactions, ROUND(SUM(o.operational_cost), 0) AS operational_cost,
       ROUND(100.0 * SUM(o.operational_cost) / SUM(SUM(o.operational_cost)) OVER (), 2) AS share_of_cost_pct
FROM support.operations o JOIN support.departments d USING (department_id)
GROUP BY d.department_name
ORDER BY operational_cost DESC;

-- @query Q07.04
-- @title Days in degraded or critical state by process and year
-- @question Are operational incidents becoming more frequent?
-- @techniques conditional aggregation, EXTRACT(YEAR)
SELECT process_name,
       COUNT(*) FILTER (WHERE operational_status <> 'Normal' AND EXTRACT(YEAR FROM operation_date) = 2023) AS bad_days_2023,
       COUNT(*) FILTER (WHERE operational_status <> 'Normal' AND EXTRACT(YEAR FROM operation_date) = 2024) AS bad_days_2024,
       COUNT(*) FILTER (WHERE operational_status <> 'Normal' AND EXTRACT(YEAR FROM operation_date) = 2025) AS bad_days_2025
FROM support.operations
GROUP BY process_name
HAVING COUNT(*) FILTER (WHERE operational_status <> 'Normal') > 10
ORDER BY bad_days_2025 DESC;

-- @query Q07.05
-- @title Peak-season processing time
-- @question Which processes slow down in November-December?
-- @techniques subquery in FROM, FILTERed weighted averages, ratio
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

-- @query Q07.06
-- @title Departmental cost by category and year
-- @question Where is departmental spend going and how fast is each category growing?
-- @techniques conditional aggregation pivot, growth calculation
SELECT cost_category,
       ROUND(SUM(total_cost) FILTER (WHERE EXTRACT(YEAR FROM cost_date) = 2023), 0) AS cost_2023,
       ROUND(SUM(total_cost) FILTER (WHERE EXTRACT(YEAR FROM cost_date) = 2024), 0) AS cost_2024,
       ROUND(SUM(total_cost) FILTER (WHERE EXTRACT(YEAR FROM cost_date) = 2025), 0) AS cost_2025,
       ROUND(100.0 * (SUM(total_cost) FILTER (WHERE EXTRACT(YEAR FROM cost_date) = 2025)
                      / SUM(total_cost) FILTER (WHERE EXTRACT(YEAR FROM cost_date) = 2023) - 1), 1) AS growth_23_25_pct
FROM support.business_costs
GROUP BY cost_category
ORDER BY cost_2025 DESC;

-- @query Q07.07
-- @title Spend vs budget by department and year
-- @question Which departments overspend their budget?
-- @techniques JOIN, GROUP BY, derived utilisation %
SELECT d.department_name, EXTRACT(YEAR FROM bc.cost_date)::int AS year,
       ROUND(SUM(bc.total_cost), 0) AS spend, d.operational_budget AS budget,
       ROUND(100.0 * SUM(bc.total_cost) / d.operational_budget, 1) AS utilisation_pct
FROM support.business_costs bc JOIN support.departments d USING (department_id)
GROUP BY d.department_name, EXTRACT(YEAR FROM bc.cost_date), d.operational_budget
ORDER BY year DESC, utilisation_pct DESC;

-- @query Q07.08
-- @title Cost per resolved ticket by department and year
-- @question How much does it cost to resolve one ticket in each department?
-- @techniques two CTEs joined on department and year
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

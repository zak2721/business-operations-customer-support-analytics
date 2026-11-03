-- =============================================================================
-- 03_data_quality / data_quality_checks.sql
-- Post-load validation. Every "violations" query is expected to return 0.
-- (Schema constraints already enforce many rules; these queries prove it and
-- cover rules that cannot be expressed as constraints.)
-- =============================================================================

-- @query DQ.01
-- @title Row counts per table
-- @question Did every table load with the expected number of rows?
-- @techniques UNION ALL, COUNT
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

-- @query DQ.02
-- @title Orphan foreign keys (LEFT JOIN anti-join)
-- @question Does every ticket and survey point to an existing parent record?
-- @techniques LEFT JOIN, IS NULL anti-join, UNION ALL
SELECT 'tickets -> customers' AS relationship, COUNT(*) AS violations
FROM support.support_tickets t LEFT JOIN support.customers c ON c.customer_id = t.customer_id WHERE c.customer_id IS NULL
UNION ALL
SELECT 'tickets -> agents (non-null)', COUNT(*)
FROM support.support_tickets t LEFT JOIN support.agents a ON a.agent_id = t.agent_id WHERE t.agent_id IS NOT NULL AND a.agent_id IS NULL
UNION ALL
SELECT 'feedback -> tickets', COUNT(*)
FROM support.customer_feedback f LEFT JOIN support.support_tickets t ON t.ticket_id = f.ticket_id WHERE t.ticket_id IS NULL;

-- @query DQ.03
-- @title Ticket chronology and status consistency
-- @question Are there impossible timestamps or open tickets with resolution dates?
-- @techniques CASE WHEN inside SUM (conditional aggregation)
SELECT SUM(CASE WHEN first_response_date < ticket_created_date THEN 1 ELSE 0 END) AS response_before_created,
       SUM(CASE WHEN resolved_date < ticket_created_date THEN 1 ELSE 0 END)       AS resolved_before_created,
       SUM(CASE WHEN resolved_date < first_response_date THEN 1 ELSE 0 END)       AS resolved_before_response,
       SUM(CASE WHEN ticket_status IN ('Open','In Progress','Pending','Cancelled') AND resolved_date IS NOT NULL THEN 1 ELSE 0 END) AS unresolved_with_resolution_date,
       SUM(CASE WHEN ticket_status IN ('Closed','Resolved') AND resolved_date IS NULL AND NOT resolution_ts_invalid THEN 1 ELSE 0 END) AS resolved_missing_date_unflagged
FROM support.support_tickets;

-- @query DQ.04
-- @title Feedback consistency with its ticket
-- @question Does each survey's customer match the ticket's customer, and come after resolution?
-- @techniques INNER JOIN, conditional aggregation
SELECT COUNT(*) FILTER (WHERE f.customer_id <> t.customer_id)                      AS customer_mismatch,
       COUNT(*) FILTER (WHERE t.resolved_date IS NOT NULL AND f.feedback_date < t.resolved_date) AS survey_before_resolution,
       COUNT(*) FILTER (WHERE f.satisfaction_score IS NULL)                         AS missing_csat,
       COUNT(*) FILTER (WHERE f.satisfaction_score_invalid)                         AS flagged_invalid_csat
FROM support.customer_feedback f JOIN support.support_tickets t ON t.ticket_id = f.ticket_id;

-- @query DQ.05
-- @title Duplicate business keys
-- @question Are there duplicate tickets or duplicate operations days per process?
-- @techniques GROUP BY ... HAVING COUNT(*) > 1
SELECT 'operations (date, process)' AS key_name, COUNT(*) AS duplicate_keys
FROM (SELECT operation_date, process_name FROM support.operations GROUP BY 1, 2 HAVING COUNT(*) > 1) x
UNION ALL
SELECT 'agent_performance (agent, month)', COUNT(*)
FROM (SELECT agent_id, performance_date FROM support.agent_performance GROUP BY 1, 2 HAVING COUNT(*) > 1) y;

-- @query DQ.06
-- @title Tickets created before customer registration or agent hire
-- @question Are any tickets dated before the customer existed or the agent was hired?
-- @techniques multi-table JOIN, date comparison
SELECT COUNT(*) FILTER (WHERE t.ticket_created_date::date < c.registration_date) AS before_registration,
       COUNT(*) FILTER (WHERE t.ticket_created_date::date < a.hire_date)         AS before_agent_hire
FROM support.support_tickets t
JOIN support.customers c ON c.customer_id = t.customer_id
LEFT JOIN support.agents a ON a.agent_id = t.agent_id;

-- @query DQ.07
-- @title Cleaning flags carried into the database
-- @question How many records carry a cleaning flag (kept but treated specially)?
-- @techniques scalar subqueries
SELECT (SELECT COUNT(*) FROM support.support_tickets WHERE agent_unknown)         AS tickets_unknown_agent,
       (SELECT COUNT(*) FROM support.support_tickets WHERE resolution_ts_invalid) AS tickets_invalid_resolution_ts,
       (SELECT COUNT(*) FROM support.support_tickets WHERE first_response_missing) AS tickets_missing_first_response,
       (SELECT COUNT(*) FROM support.customers WHERE clv_imputed)                 AS customers_clv_imputed,
       (SELECT COUNT(*) FROM support.operations WHERE cost_outlier)               AS ops_cost_outliers_replaced,
       (SELECT COUNT(*) FROM support.operations WHERE processing_time_imputed)    AS ops_processing_time_imputed;

-- @query DQ.08
-- @title Calendar coverage
-- @question Does the date dimension cover every ticket date without gaps?
-- @techniques LEAD window function for gap detection, scalar subqueries
SELECT (SELECT MIN(date) FROM support.calendar) AS calendar_start,
       (SELECT MAX(date) FROM support.calendar) AS calendar_end,
       (SELECT COUNT(*) FROM (SELECT date, LEAD(date) OVER (ORDER BY date) - date AS gap FROM support.calendar) g WHERE gap > 1) AS gaps,
       (SELECT COUNT(*) FROM support.support_tickets t WHERE NOT EXISTS
            (SELECT 1 FROM support.calendar c WHERE c.date = t.ticket_created_date::date)) AS ticket_dates_missing;

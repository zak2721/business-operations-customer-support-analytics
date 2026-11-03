-- =============================================================================
-- 06_agent_performance / agent_performance.sql
-- =============================================================================

-- @query Q06.01
-- @title Agent scorecard
-- @question How does each agent perform on volume, speed, SLA, quality and satisfaction?
-- @techniques reporting view, ORDER BY
SELECT agent_name, department_name, experience_level, tickets_assigned, tickets_resolved, productivity_pct,
       avg_resolution_h, sla_compliance_pct, reopen_pct, avg_csat
FROM support.v_agent_scorecard
ORDER BY tickets_resolved DESC
LIMIT 20;

-- @query Q06.02
-- @title Agent ranking within department (RANK, DENSE_RANK, ROW_NUMBER)
-- @question Who are the top performers in each department by SLA compliance?
-- @techniques window functions RANK / DENSE_RANK / ROW_NUMBER with PARTITION BY
WITH s AS (SELECT * FROM support.v_agent_scorecard WHERE tickets_resolved >= 100)
SELECT department_name, agent_name, experience_level, sla_compliance_pct, avg_csat,
       RANK()       OVER (PARTITION BY department_name ORDER BY sla_compliance_pct DESC) AS sla_rank,
       DENSE_RANK() OVER (PARTITION BY department_name ORDER BY ROUND(avg_csat, 1) DESC) AS csat_dense_rank,
       ROW_NUMBER() OVER (PARTITION BY department_name ORDER BY tickets_resolved DESC)   AS volume_row
FROM s
ORDER BY department_name, sla_rank;

-- @query Q06.03
-- @title Performance by experience level
-- @question How do Junior, Mid-Level, Senior and Lead agents compare?
-- @techniques GROUP BY, CASE ordering
SELECT experience_level, COUNT(DISTINCT agent_id) AS agents, COUNT(*) AS tickets,
       ROUND((AVG(resolution_hours) FILTER (WHERE sla_eligible))::numeric, 2) AS avg_resolution_h,
       ROUND(100.0 * COUNT(*) FILTER (WHERE sla_met) / COUNT(*) FILTER (WHERE sla_eligible), 2) AS sla_pct,
       ROUND(100.0 * COUNT(*) FILTER (WHERE is_reopened) / COUNT(*) FILTER (WHERE is_resolved), 2) AS reopen_pct,
       ROUND(AVG(satisfaction_score)::numeric, 2) AS avg_csat
FROM support.v_ticket_metrics
WHERE agent_id IS NOT NULL
GROUP BY experience_level
ORDER BY CASE experience_level WHEN 'Junior' THEN 1 WHEN 'Mid-Level' THEN 2 WHEN 'Senior' THEN 3 ELSE 4 END;

-- @query Q06.04
-- @title Agents with unusually high workload
-- @question Which agents carry a monthly workload well above their department average?
-- @techniques CTE, AVG() OVER (PARTITION BY), HAVING-style filter on window result
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

-- @query Q06.05
-- @title Tickets assigned vs resolved per agent (RIGHT JOIN)
-- @question Do any agents (including those with no tickets) have a gap between assigned and resolved?
-- @techniques RIGHT JOIN (keeps every agent), COALESCE
SELECT a.agent_id, a.agent_name, a.employment_status,
       COALESCE(x.assigned, 0) AS assigned, COALESCE(x.resolved, 0) AS resolved,
       COALESCE(x.assigned, 0) - COALESCE(x.resolved, 0) AS gap
FROM (SELECT agent_id, COUNT(*) AS assigned, COUNT(*) FILTER (WHERE ticket_status IN ('Closed','Resolved')) AS resolved
      FROM support.support_tickets GROUP BY agent_id) x
RIGHT JOIN support.agents a ON a.agent_id = x.agent_id
ORDER BY gap DESC
LIMIT 15;

-- @query Q06.06
-- @title Agent monthly trend with LAG/LEAD
-- @question How did each Billing agent's monthly resolutions change month to month?
-- @techniques LAG, LEAD, PARTITION BY agent
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

-- @query Q06.07
-- @title Quartiles of agents by SLA compliance (NTILE)
-- @question How large is the gap between top-quartile and bottom-quartile agents?
-- @techniques NTILE, CTE, aggregation of window output
WITH q AS (
    SELECT *, NTILE(4) OVER (ORDER BY sla_compliance_pct DESC) AS quartile
    FROM support.v_agent_scorecard WHERE tickets_resolved >= 100
)
SELECT quartile, COUNT(*) AS agents, ROUND(AVG(sla_compliance_pct), 2) AS avg_sla_pct,
       ROUND(AVG(avg_csat), 2) AS avg_csat, ROUND(AVG(reopen_pct), 2) AS avg_reopen_pct,
       STRING_AGG(DISTINCT experience_level, ', ') AS experience_levels
FROM q GROUP BY quartile ORDER BY quartile;

-- =============================================================================
-- 05_customer_support_analysis / customer_support_analysis.sql
-- =============================================================================

-- @query Q05.01
-- @title Ticket status distribution
-- @question What share of tickets is in each status at the snapshot date?
-- @techniques GROUP BY, window SUM() OVER () for share of total
SELECT ticket_status, COUNT(*) AS tickets,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS share_pct
FROM support.support_tickets
GROUP BY ticket_status
ORDER BY tickets DESC;

-- @query Q05.02
-- @title Ticket volume by category and subcategory
-- @question Which categories and subcategories generate the most workload?
-- @techniques GROUP BY ROLLUP, ORDER BY
SELECT COALESCE(ticket_category, 'ALL') AS category, COALESCE(ticket_subcategory, 'Subtotal') AS subcategory,
       COUNT(*) AS tickets
FROM support.support_tickets
GROUP BY ROLLUP (ticket_category, ticket_subcategory)
ORDER BY ticket_category NULLS LAST, tickets DESC;

-- @query Q05.03
-- @title Response and resolution by channel
-- @question Which support channels have the longest response and resolution times?
-- @techniques reporting view, ORDER BY
SELECT * FROM support.v_channel_performance ORDER BY avg_frt_h DESC;

-- @query Q05.04
-- @title Resolution time by priority vs SLA target
-- @question Which priorities take longest relative to their SLA targets?
-- @techniques AVG / PERCENTILE_CONT with FILTER, CASE ordering
SELECT ticket_priority, MIN(sla_target_hours) AS sla_target_h,
       COUNT(*) FILTER (WHERE sla_eligible) AS resolved,
       ROUND((AVG(resolution_hours) FILTER (WHERE sla_eligible))::numeric, 2) AS avg_resolution_h,
       ROUND((PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY resolution_hours) FILTER (WHERE sla_eligible))::numeric, 2) AS median_resolution_h,
       ROUND((PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY resolution_hours) FILTER (WHERE sla_eligible))::numeric, 2) AS p90_resolution_h,
       ROUND(100.0 * COUNT(*) FILTER (WHERE sla_met) / COUNT(*) FILTER (WHERE sla_eligible), 2) AS sla_compliance_pct
FROM support.v_ticket_metrics
GROUP BY ticket_priority
ORDER BY CASE ticket_priority WHEN 'Critical' THEN 1 WHEN 'High' THEN 2 WHEN 'Medium' THEN 3 ELSE 4 END;

-- @query Q05.05
-- @title Ticket volume by weekday and hour band
-- @question When does demand peak during the week?
-- @techniques EXTRACT(ISODOW/HOUR), CASE bucketing, conditional aggregation (pivot)
SELECT TO_CHAR(ticket_created_date, 'ID-Dy') AS weekday,
       COUNT(*) FILTER (WHERE EXTRACT(HOUR FROM ticket_created_date) < 8)                 AS "00-08",
       COUNT(*) FILTER (WHERE EXTRACT(HOUR FROM ticket_created_date) BETWEEN 8 AND 11)    AS "08-12",
       COUNT(*) FILTER (WHERE EXTRACT(HOUR FROM ticket_created_date) BETWEEN 12 AND 16)   AS "12-17",
       COUNT(*) FILTER (WHERE EXTRACT(HOUR FROM ticket_created_date) BETWEEN 17 AND 19)   AS "17-20",
       COUNT(*) FILTER (WHERE EXTRACT(HOUR FROM ticket_created_date) >= 20)               AS "20-24",
       COUNT(*) AS total
FROM support.support_tickets
GROUP BY 1 ORDER BY 1;

-- @query Q05.06
-- @title Escalations and reopenings by category
-- @question Which categories drive escalations and reopened tickets?
-- @techniques conditional aggregation, NULLIF for safe division
SELECT ticket_category,
       COUNT(*) AS tickets,
       COUNT(*) FILTER (WHERE is_escalated) AS escalated,
       ROUND(100.0 * COUNT(*) FILTER (WHERE is_escalated) / NULLIF(COUNT(*) FILTER (WHERE NOT is_cancelled), 0), 2) AS escalation_pct,
       COUNT(*) FILTER (WHERE is_reopened) AS reopened,
       ROUND(100.0 * COUNT(*) FILTER (WHERE is_reopened) / NULLIF(COUNT(*) FILTER (WHERE is_resolved), 0), 2) AS reopen_pct
FROM support.v_ticket_metrics
GROUP BY ticket_category
ORDER BY escalation_pct DESC;

-- @query Q05.07
-- @title First contact resolution by channel and category
-- @question Where are tickets solved in a single interaction?
-- @techniques GROUP BY two dimensions, HAVING on volume
SELECT support_channel, ticket_category,
       COUNT(*) FILTER (WHERE sla_eligible) AS resolved,
       ROUND(100.0 * COUNT(*) FILTER (WHERE is_fcr) / NULLIF(COUNT(*) FILTER (WHERE sla_eligible), 0), 2) AS fcr_pct
FROM support.v_ticket_metrics
WHERE support_channel <> 'Unknown'
GROUP BY support_channel, ticket_category
HAVING COUNT(*) FILTER (WHERE sla_eligible) >= 100
ORDER BY fcr_pct DESC
LIMIT 15;

-- @query Q05.08
-- @title Open backlog by aging bucket
-- @question How old is the open backlog and how much of it is already past SLA?
-- @techniques reporting view, ORDER BY
SELECT * FROM support.v_backlog_aging ORDER BY aging_bucket;

-- @query Q05.09
-- @title Oldest open tickets (aging list)
-- @question Which open tickets have waited longest and who owns them?
-- @techniques multi-table JOIN, LEFT JOIN for unknown agents, ORDER BY ... LIMIT
SELECT v.ticket_id, v.ticket_status, v.ticket_priority, v.ticket_category, v.department_name,
       COALESCE(v.agent_name, '(unassigned / unknown)') AS agent, ROUND(v.ticket_age_days::numeric, 1) AS age_days
FROM support.v_ticket_metrics v
WHERE v.is_unresolved
ORDER BY v.ticket_age_days DESC
LIMIT 15;

-- @query Q05.10
-- @title CSAT by first response time band
-- @question Is customer satisfaction associated with how fast the first response arrives?
-- @techniques CASE bucketing, AVG, ordering by band
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

-- @query Q05.11
-- @title CSAT by channel with SLA outcome
-- @question Does an SLA breach hurt satisfaction equally on every channel?
-- @techniques conditional AVG with FILTER, derived difference column
SELECT support_channel,
       ROUND((AVG(satisfaction_score) FILTER (WHERE sla_met))::numeric, 2)          AS csat_within_sla,
       ROUND((AVG(satisfaction_score) FILTER (WHERE sla_met = FALSE))::numeric, 2)  AS csat_breached,
       ROUND((AVG(satisfaction_score) FILTER (WHERE sla_met) - AVG(satisfaction_score) FILTER (WHERE sla_met = FALSE))::numeric, 2) AS csat_gap
FROM support.v_ticket_metrics
WHERE support_channel <> 'Unknown'
GROUP BY support_channel
ORDER BY csat_gap DESC;

-- @query Q05.12
-- @title Feedback themes
-- @question What do customers talk about in surveys, and how satisfied is each theme?
-- @techniques GROUP BY, DISTINCT inside aggregate
SELECT feedback_category, COUNT(*) AS responses, COUNT(DISTINCT customer_id) AS customers,
       ROUND(AVG(satisfaction_score)::numeric, 2) AS avg_csat,
       COUNT(customer_comment) AS with_comment
FROM support.customer_feedback
GROUP BY feedback_category
ORDER BY responses DESC;

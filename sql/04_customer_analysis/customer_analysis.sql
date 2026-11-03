-- =============================================================================
-- 04_customer_analysis / customer_analysis.sql
-- =============================================================================

-- @query Q04.01
-- @title Customer base by segment
-- @question How are customers and lifetime value distributed across segments?
-- @techniques SELECT, GROUP BY, ORDER BY, aggregate functions
SELECT customer_segment,
       COUNT(*)                                    AS customers,
       ROUND(AVG(customer_lifetime_value), 0)      AS avg_clv,
       ROUND((PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY customer_lifetime_value))::numeric, 0) AS median_clv,
       ROUND(SUM(customer_lifetime_value), 0)      AS total_clv
FROM support.customers
GROUP BY customer_segment
ORDER BY total_clv DESC;

-- @query Q04.02
-- @title Customers by region and country
-- @question Which regions and countries hold the most customers?
-- @techniques WHERE, GROUP BY, HAVING, ORDER BY
SELECT customer_region, customer_country, COUNT(*) AS customers
FROM support.customers
WHERE customer_status <> 'Churned'
GROUP BY customer_region, customer_country
HAVING COUNT(*) >= 50
ORDER BY customer_region, customers DESC;

-- @query Q04.03
-- @title New customer registrations per year
-- @question How fast is the customer base growing?
-- @techniques DATE_PART, GROUP BY, LAG for year-over-year growth
SELECT reg_year, new_customers,
       ROUND(100.0 * (new_customers - LAG(new_customers) OVER (ORDER BY reg_year))
             / NULLIF(LAG(new_customers) OVER (ORDER BY reg_year), 0), 1) AS yoy_growth_pct
FROM (SELECT DATE_PART('year', registration_date)::int AS reg_year, COUNT(*) AS new_customers
      FROM support.customers GROUP BY 1) y
ORDER BY reg_year;

-- @query Q04.04
-- @title Distinct contacting customers per year
-- @question How many distinct customers contacted support each year?
-- @techniques COUNT(DISTINCT), DATE_TRUNC
SELECT DATE_PART('year', ticket_created_date)::int AS year,
       COUNT(DISTINCT customer_id)                 AS contacting_customers,
       COUNT(*)                                    AS tickets,
       ROUND(COUNT(*)::numeric / COUNT(DISTINCT customer_id), 2) AS tickets_per_contacting_customer
FROM support.support_tickets
GROUP BY 1 ORDER BY 1;

-- @query Q04.05
-- @title Customer contact-frequency segmentation
-- @question How many customers are light, regular or heavy support users, and what is their value?
-- @techniques CTE, CASE WHEN bucketing, LEFT JOIN (customers without tickets)
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

-- @query Q04.06
-- @title Top 15 customers by ticket volume (repeat contacts)
-- @question Which customers generate the most repeated support requests?
-- @techniques view reuse, GROUP BY, ORDER BY ... LIMIT
SELECT customer_id, customer_segment, customer_region, tickets, repeat_contacts, escalations, avg_csat,
       customer_lifetime_value
FROM support.v_customer_360
ORDER BY tickets DESC, repeat_contacts DESC
LIMIT 15;

-- @query Q04.07
-- @title Support experience by customer status
-- @question Do churned customers show worse support experience than active ones?
-- @techniques INNER JOIN to view, conditional aggregation
SELECT c.customer_status,
       COUNT(*) AS tickets,
       ROUND(AVG(v.satisfaction_score)::numeric, 2) AS avg_csat,
       ROUND(100.0 * COUNT(*) FILTER (WHERE v.sla_met) / NULLIF(COUNT(*) FILTER (WHERE v.sla_eligible), 0), 2) AS sla_pct,
       ROUND(100.0 * COUNT(*) FILTER (WHERE v.is_escalated) / COUNT(*), 2) AS escalation_pct
FROM support.v_ticket_metrics v
JOIN support.customers c ON c.customer_id = v.customer_id
GROUP BY c.customer_status
ORDER BY avg_csat;

-- @query Q04.08
-- @title Customers whose CSAT is below their segment average
-- @question Which high-value customers are less satisfied than their peers?
-- @techniques correlated subquery, HAVING
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

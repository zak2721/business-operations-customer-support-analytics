-- =============================================================================
-- 03_create_indexes.sql
-- Indexes chosen for the query patterns in folders 04-09: FK joins, date-range
-- filters and the most common GROUP BY columns. PKs/UNIQUEs are indexed already.
-- =============================================================================
SET search_path TO support;

CREATE INDEX IF NOT EXISTS ix_tickets_customer     ON support_tickets (customer_id, ticket_created_date);
CREATE INDEX IF NOT EXISTS ix_tickets_agent        ON support_tickets (agent_id);
CREATE INDEX IF NOT EXISTS ix_tickets_department   ON support_tickets (department_id);
CREATE INDEX IF NOT EXISTS ix_tickets_created      ON support_tickets (ticket_created_date);
CREATE INDEX IF NOT EXISTS ix_tickets_status       ON support_tickets (ticket_status);
CREATE INDEX IF NOT EXISTS ix_tickets_prio_channel ON support_tickets (ticket_priority, support_channel);
-- partial index: the open backlog is small and queried often
CREATE INDEX IF NOT EXISTS ix_tickets_open         ON support_tickets (ticket_created_date)
    WHERE ticket_status IN ('Open','In Progress','Pending');

CREATE INDEX IF NOT EXISTS ix_feedback_customer    ON customer_feedback (customer_id);
CREATE INDEX IF NOT EXISTS ix_feedback_date        ON customer_feedback (feedback_date);
CREATE INDEX IF NOT EXISTS ix_ops_dept_date        ON operations (department_id, operation_date);
CREATE INDEX IF NOT EXISTS ix_perf_date            ON agent_performance (performance_date);
CREATE INDEX IF NOT EXISTS ix_costs_dept_date      ON business_costs (department_id, cost_date);
CREATE INDEX IF NOT EXISTS ix_agents_department    ON agents (department_id);

ANALYZE;

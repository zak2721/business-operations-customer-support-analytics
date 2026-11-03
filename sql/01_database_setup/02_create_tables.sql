-- =============================================================================
-- 02_create_tables.sql
-- Normalised (3NF) schema for the cleaned datasets, with primary keys, foreign
-- keys, CHECK constraints that encode the business rules, and sensible types.
-- Idempotent: drops and recreates the `support` schema.
-- =============================================================================
DROP SCHEMA IF EXISTS support CASCADE;
CREATE SCHEMA support;
SET search_path TO support;

-- ---------------------------------------------------------------- dimensions
CREATE TABLE departments (
    department_id        VARCHAR(10)  PRIMARY KEY,
    department_name      VARCHAR(60)  NOT NULL UNIQUE,
    department_manager   VARCHAR(80)  NOT NULL,
    department_location  VARCHAR(60),
    operational_budget   NUMERIC(14,2) NOT NULL CHECK (operational_budget >= 0)
);

CREATE TABLE agents (
    agent_id           VARCHAR(10) PRIMARY KEY,
    agent_name         VARCHAR(80) NOT NULL,
    team               VARCHAR(60) NOT NULL,
    department_id      VARCHAR(10) NOT NULL REFERENCES departments(department_id),
    hire_date          DATE        NOT NULL,
    experience_level   VARCHAR(20) NOT NULL CHECK (experience_level IN ('Junior','Mid-Level','Senior','Lead')),
    employment_status  VARCHAR(20) NOT NULL CHECK (employment_status IN ('Active','On Leave','Terminated')),
    shift              VARCHAR(20),
    location           VARCHAR(60)
);

CREATE TABLE customers (
    customer_id              VARCHAR(12)  PRIMARY KEY,
    customer_name            VARCHAR(120) NOT NULL,
    customer_segment         VARCHAR(20)  NOT NULL CHECK (customer_segment IN ('Enterprise','Mid-Market','Small Business','Consumer')),
    customer_region          VARCHAR(40)  NOT NULL,
    customer_country         VARCHAR(60)  NOT NULL,
    customer_type            VARCHAR(20)  NOT NULL CHECK (customer_type IN ('Business','Individual')),
    registration_date        DATE         NOT NULL,
    customer_status          VARCHAR(20)  NOT NULL CHECK (customer_status IN ('Active','Inactive','Churned')),
    customer_lifetime_value  NUMERIC(14,2) NOT NULL CHECK (customer_lifetime_value >= 0),
    clv_imputed              BOOLEAN      NOT NULL DEFAULT FALSE
);

CREATE TABLE calendar (
    date           DATE PRIMARY KEY,
    year           SMALLINT NOT NULL,
    quarter        SMALLINT NOT NULL CHECK (quarter BETWEEN 1 AND 4),
    month          SMALLINT NOT NULL CHECK (month BETWEEN 1 AND 12),
    month_name     VARCHAR(12) NOT NULL,
    week           SMALLINT NOT NULL,
    day            SMALLINT NOT NULL,
    day_name       VARCHAR(12) NOT NULL,
    weekday_flag   SMALLINT NOT NULL CHECK (weekday_flag IN (0,1)),
    year_month     CHAR(7) NOT NULL,
    quarter_label  CHAR(7) NOT NULL
);

-- --------------------------------------------------------------------- facts
CREATE TABLE support_tickets (
    ticket_id               VARCHAR(12) PRIMARY KEY,
    customer_id             VARCHAR(12) NOT NULL REFERENCES customers(customer_id),
    agent_id                VARCHAR(10) REFERENCES agents(agent_id),          -- NULL = unknown agent (flagged in cleaning)
    department_id           VARCHAR(10) NOT NULL REFERENCES departments(department_id),
    ticket_created_date     TIMESTAMP   NOT NULL,
    first_response_date     TIMESTAMP,
    resolved_date           TIMESTAMP,
    ticket_category         VARCHAR(40) NOT NULL,
    ticket_subcategory      VARCHAR(40) NOT NULL,
    ticket_priority         VARCHAR(10) NOT NULL CHECK (ticket_priority IN ('Critical','High','Medium','Low')),
    ticket_status           VARCHAR(15) NOT NULL CHECK (ticket_status IN ('Open','In Progress','Pending','Resolved','Closed','Cancelled')),
    support_channel         VARCHAR(20) NOT NULL CHECK (support_channel IN ('Email','Phone','Live Chat','Web Portal','Social Media','Unknown')),
    resolution_type         VARCHAR(40),
    reopened_count          SMALLINT    NOT NULL DEFAULT 0 CHECK (reopened_count >= 0),
    escalation_flag         SMALLINT    NOT NULL DEFAULT 0 CHECK (escalation_flag IN (0,1)),
    sla_target_hours        SMALLINT    NOT NULL CHECK (sla_target_hours > 0),
    agent_unknown           BOOLEAN     NOT NULL DEFAULT FALSE,
    resolution_ts_invalid   BOOLEAN     NOT NULL DEFAULT FALSE,
    first_response_missing  BOOLEAN     NOT NULL DEFAULT FALSE,
    -- business rules
    CONSTRAINT chk_response_after_created CHECK (first_response_date IS NULL OR first_response_date >= ticket_created_date),
    CONSTRAINT chk_resolved_after_created CHECK (resolved_date IS NULL OR resolved_date >= ticket_created_date),
    CONSTRAINT chk_open_has_no_resolution CHECK (ticket_status IN ('Resolved','Closed') OR resolved_date IS NULL),
    CONSTRAINT chk_sla_matches_priority CHECK (
        (ticket_priority = 'Critical' AND sla_target_hours = 8)  OR (ticket_priority = 'High' AND sla_target_hours = 24) OR
        (ticket_priority = 'Medium'   AND sla_target_hours = 48) OR (ticket_priority = 'Low'  AND sla_target_hours = 72))
);

CREATE TABLE customer_feedback (
    feedback_id                 VARCHAR(12) PRIMARY KEY,
    ticket_id                   VARCHAR(12) NOT NULL UNIQUE REFERENCES support_tickets(ticket_id),  -- max one survey per ticket
    customer_id                 VARCHAR(12) NOT NULL REFERENCES customers(customer_id),
    feedback_date               TIMESTAMP   NOT NULL,
    satisfaction_score          SMALLINT    CHECK (satisfaction_score BETWEEN 1 AND 5),
    customer_rating             SMALLINT    CHECK (customer_rating BETWEEN 1 AND 10),
    feedback_category           VARCHAR(40),
    customer_comment            TEXT,
    satisfaction_score_invalid  BOOLEAN     NOT NULL DEFAULT FALSE
);

CREATE TABLE operations (
    operation_id               VARCHAR(12) PRIMARY KEY,
    department_id              VARCHAR(10) NOT NULL REFERENCES departments(department_id),
    operation_date             DATE        NOT NULL,
    operation_type             VARCHAR(40) NOT NULL,
    process_name               VARCHAR(60) NOT NULL,
    total_transactions         INTEGER     NOT NULL CHECK (total_transactions >= 0),
    successful_transactions    INTEGER     NOT NULL CHECK (successful_transactions >= 0),
    failed_transactions        INTEGER     NOT NULL CHECK (failed_transactions >= 0),
    processing_time_minutes    NUMERIC(10,2) NOT NULL CHECK (processing_time_minutes >= 0),
    operational_cost           NUMERIC(14,2) NOT NULL CHECK (operational_cost >= 0),
    operational_status         VARCHAR(15) NOT NULL CHECK (operational_status IN ('Normal','Degraded','Critical')),
    cost_sign_corrected        BOOLEAN NOT NULL DEFAULT FALSE,
    cost_outlier               BOOLEAN NOT NULL DEFAULT FALSE,
    operational_cost_original  NUMERIC(14,2),
    processing_time_imputed    BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT chk_txn_balance CHECK (successful_transactions + failed_transactions = total_transactions),
    CONSTRAINT uq_ops_day_process UNIQUE (operation_date, process_name)
);

CREATE TABLE agent_performance (
    performance_id               VARCHAR(12) PRIMARY KEY,
    agent_id                     VARCHAR(10) NOT NULL REFERENCES agents(agent_id),
    performance_date             DATE        NOT NULL,   -- month end
    tickets_assigned             INTEGER     NOT NULL CHECK (tickets_assigned >= 0),
    tickets_resolved             INTEGER     NOT NULL CHECK (tickets_resolved >= 0),
    average_response_time        NUMERIC(10,2),
    average_resolution_time      NUMERIC(10,2),
    customer_satisfaction_score  NUMERIC(4,2) CHECK (customer_satisfaction_score BETWEEN 1 AND 5),
    sla_compliance_rate          NUMERIC(6,2) CHECK (sla_compliance_rate BETWEEN 0 AND 100),
    workload_hours               NUMERIC(8,1) NOT NULL CHECK (workload_hours >= 0),
    CONSTRAINT uq_agent_month UNIQUE (agent_id, performance_date)
);

CREATE TABLE business_costs (
    cost_id        VARCHAR(12) PRIMARY KEY,
    department_id  VARCHAR(10) NOT NULL REFERENCES departments(department_id),
    cost_date      DATE        NOT NULL,   -- month start
    cost_category  VARCHAR(40) NOT NULL,
    direct_cost    NUMERIC(14,2) NOT NULL CHECK (direct_cost >= 0),
    indirect_cost  NUMERIC(14,2) NOT NULL CHECK (indirect_cost >= 0),
    total_cost     NUMERIC(14,2) NOT NULL CHECK (total_cost >= 0),
    CONSTRAINT chk_cost_total CHECK (ABS(total_cost - (direct_cost + indirect_cost)) <= 0.02),
    CONSTRAINT uq_cost_month UNIQUE (department_id, cost_date, cost_category)
);

COMMENT ON TABLE support_tickets IS 'One row per support ticket. Cleaned; see data/reports/data_quality_report.md';
COMMENT ON COLUMN support_tickets.resolution_ts_invalid IS 'Raw resolution timestamp preceded creation; nulled and excluded from time/SLA KPIs';
COMMENT ON COLUMN operations.cost_outlier IS 'Cost replaced by process-month median cost/txn x volume; original in operational_cost_original';

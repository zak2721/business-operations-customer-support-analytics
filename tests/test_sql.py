"""SQL layer: Python and PostgreSQL produce identical KPIs; constraints enforce business rules.

Skipped automatically when no PostgreSQL connection is available (see .env.example).
"""
import json

import pandas as pd
import psycopg2
import pytest

from src import config
from src.analytics import eda
from src.database.run_sql import all_queries


@pytest.fixture(scope="module")
def conn():
    try:
        from src.database.load_postgres import connect
        c = connect()
        with c.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM support.support_tickets")
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"PostgreSQL not available: {e}")
    yield c
    c.close()


def q(conn, sql):
    return pd.read_sql_query(sql, conn)


def test_at_least_40_analytical_queries_defined():
    qs = all_queries()
    assert sum(x.qid.startswith("Q") for x in qs) >= 40
    assert all(x.title and x.question and x.techniques for x in qs)


def test_row_counts_match_processed(conn, processed):
    for table in ("customers", "support_tickets", "customer_feedback", "operations", "business_costs"):
        n = q(conn, f"SELECT COUNT(*) AS n FROM support.{table}").n.iloc[0]
        assert n == len(processed[table]), table


def test_sql_kpis_equal_python(conn):
    s = q(conn, "SELECT * FROM support.v_kpi_summary").iloc[0]
    p = json.loads((config.REPORTS_DATA_DIR / "kpi_summary.json").read_text())
    pairs = {
        "total_tickets": "Total Tickets", "open_tickets": "Open Tickets", "closed_tickets": "Closed Tickets",
        "escalated_tickets": "Escalated Tickets", "reopened_tickets": "Reopened Tickets",
        "avg_first_response_h": "Avg First Response Time (h)", "avg_resolution_h": "Avg Resolution Time (h)",
        "fcr_rate_pct": "First Contact Resolution Rate (%)", "sla_compliance_pct": "SLA Compliance Rate (%)",
        "sla_breach_pct": "SLA Breach Rate (%)", "resolution_rate_pct": "Ticket Resolution Rate (%)",
        "avg_csat": "Avg Customer Satisfaction (1-5)", "csat_rate_pct": "Customer Satisfaction Rate (%)",
        "repeat_contact_pct": "Customer Repeat Contact Rate (%)", "total_transactions": "Total Transactions",
        "operational_success_pct": "Operational Success Rate (%)", "cost_per_resolved_ticket": "Cost per Resolved Ticket ($)",
        "avg_processing_min": "Avg Processing Time (min)",
    }
    for sql_col, py_key in pairs.items():
        assert float(s[sql_col]) == pytest.approx(p[py_key], abs=0.011), sql_col


def test_sql_backlog_equals_python(conn, processed):
    sql = {r.month: r.open_at_month_end for r in q(conn, [x for x in all_queries() if x.qid == "Q08.05"][0].sql).itertuples()}
    py = eda.monthly_backlog(processed["tickets_enriched"]).set_index("month").open_at_month_end
    for m, n in sql.items():
        assert py[m] == n, m


def test_data_quality_checks_all_zero(conn):
    for qid in ("DQ.02", "DQ.03", "DQ.05", "DQ.06"):
        df = q(conn, [x for x in all_queries() if x.qid == qid][0].sql)
        assert df.select_dtypes("number").to_numpy().sum() == 0, qid


@pytest.mark.parametrize("bad_sql", [
    "INSERT INTO support.support_tickets (ticket_id, customer_id, department_id, ticket_created_date, resolved_date, "
    "ticket_category, ticket_subcategory, ticket_priority, ticket_status, support_channel, sla_target_hours) "
    "VALUES ('X1','CUS-00001','DEP-01','2025-01-02','2025-01-01','c','s','High','Closed','Email',24)",   # resolved before created
    "INSERT INTO support.support_tickets (ticket_id, customer_id, department_id, ticket_created_date, "
    "ticket_category, ticket_subcategory, ticket_priority, ticket_status, support_channel, sla_target_hours) "
    "VALUES ('X2','CUS-00001','DEP-01','2025-01-02','c','s','High','Open','Email',48)",                 # SLA != priority rule
    "INSERT INTO support.customer_feedback (feedback_id, ticket_id, customer_id, feedback_date, satisfaction_score) "
    "VALUES ('F1','TCK-000001','CUS-00001','2025-01-01', 7)",                                            # CSAT out of range
])
def test_constraints_reject_invalid_rows(conn, bad_sql):
    with conn.cursor() as cur:
        with pytest.raises(psycopg2.Error):
            cur.execute(bad_sql)
    conn.rollback()

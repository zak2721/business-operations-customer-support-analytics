"""Load cleaned datasets into PostgreSQL.

Run (after the cleaning pipeline):
    python -m src.database.load_postgres            # create schema + load + verify
    python -m src.database.load_postgres --no-ddl   # reload data only

Connection settings come from environment variables (PGHOST, PGPORT,
PGDATABASE, PGUSER, PGPASSWORD) - see .env.example. Nothing is hard-coded.
"""
from __future__ import annotations

import argparse
import io
import logging
import os

import pandas as pd
import psycopg2

from src import config
from src.data_cleaning.loader import load_processed

log = logging.getLogger(__name__)

# table -> columns loaded (schema order). FK order matters.
TABLES: dict[str, list[str]] = {
    "departments": ["department_id", "department_name", "department_manager", "department_location", "operational_budget"],
    "agents": ["agent_id", "agent_name", "team", "department_id", "hire_date", "experience_level", "employment_status",
               "shift", "location"],
    "customers": ["customer_id", "customer_name", "customer_segment", "customer_region", "customer_country",
                  "customer_type", "registration_date", "customer_status", "customer_lifetime_value", "clv_imputed"],
    "calendar": ["date", "year", "quarter", "month", "month_name", "week", "day", "day_name", "weekday_flag",
                 "year_month", "quarter_label"],
    "support_tickets": ["ticket_id", "customer_id", "agent_id", "department_id", "ticket_created_date",
                        "first_response_date", "resolved_date", "ticket_category", "ticket_subcategory",
                        "ticket_priority", "ticket_status", "support_channel", "resolution_type", "reopened_count",
                        "escalation_flag", "sla_target_hours", "agent_unknown", "resolution_ts_invalid",
                        "first_response_missing"],
    "customer_feedback": ["feedback_id", "ticket_id", "customer_id", "feedback_date", "satisfaction_score",
                          "customer_rating", "feedback_category", "customer_comment", "satisfaction_score_invalid"],
    "operations": ["operation_id", "department_id", "operation_date", "operation_type", "process_name",
                   "total_transactions", "successful_transactions", "failed_transactions", "processing_time_minutes",
                   "operational_cost", "operational_status", "cost_sign_corrected", "cost_outlier",
                   "operational_cost_original", "processing_time_imputed"],
    "agent_performance": ["performance_id", "agent_id", "performance_date", "tickets_assigned", "tickets_resolved",
                          "average_response_time", "average_resolution_time", "customer_satisfaction_score",
                          "sla_compliance_rate", "workload_hours"],
    "business_costs": ["cost_id", "department_id", "cost_date", "cost_category", "direct_cost", "indirect_cost",
                       "total_cost"],
}
DATE_ONLY = {"hire_date", "registration_date", "date", "operation_date", "performance_date", "cost_date"}
INT_COLS = {"satisfaction_score", "customer_rating"}


def connect(dbname: str | None = None):
    p = config.pg_dsn()
    if dbname:
        p["dbname"] = dbname
    return psycopg2.connect(**{k: v for k, v in p.items() if v not in ("", None)})


def ensure_database() -> None:
    """Create the target database if it does not exist (connects to 'postgres')."""
    target = config.pg_dsn()["dbname"]
    conn = connect("postgres")
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (target,))
        if not cur.fetchone():
            cur.execute(f'CREATE DATABASE "{target}"')
            log.info("Created database %s", target)
    conn.close()


def run_sql_file(conn, path) -> None:
    with conn.cursor() as cur:
        cur.execute(path.read_text())
    conn.commit()


def _to_copy_buffer(df: pd.DataFrame, cols: list[str]) -> io.StringIO:
    out = df[cols].copy()
    for c in cols:
        if c in DATE_ONLY:
            out[c] = pd.to_datetime(out[c]).dt.strftime("%Y-%m-%d")
        elif c in INT_COLS:
            out[c] = out[c].astype("Int64")
    buf = io.StringIO()
    out.to_csv(buf, index=False, header=False, na_rep="\\N", date_format="%Y-%m-%d %H:%M:%S")
    buf.seek(0)
    return buf


def load_all(create_schema: bool = True) -> dict[str, int]:
    ensure_database()
    conn = connect()
    if create_schema:
        for f in ("02_create_tables.sql",):
            run_sql_file(conn, config.SQL_DIR / "01_database_setup" / f)
    counts = {}
    with conn.cursor() as cur:
        cur.execute("SET search_path TO support")
        cur.execute("TRUNCATE " + ", ".join(reversed(list(TABLES))) + " CASCADE")
        for table, cols in TABLES.items():
            df = load_processed(table)
            cur.copy_expert(f"COPY {table} ({', '.join(cols)}) FROM STDIN WITH (FORMAT csv, NULL '\\N')",
                            _to_copy_buffer(df, cols))
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            n = cur.fetchone()[0]
            assert n == len(df), f"{table}: loaded {n} rows, expected {len(df)}"
            counts[table] = n
            log.info("loaded %-20s %7d rows", table, n)
    conn.commit()
    if create_schema:
        run_sql_file(conn, config.SQL_DIR / "01_database_setup" / "03_create_indexes.sql")
    conn.close()
    return counts


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-ddl", action="store_true", help="skip schema (re)creation")
    a = ap.parse_args()
    load_all(create_schema=not a.no_ddl)


if __name__ == "__main__":
    os.environ.setdefault("PGDATABASE", "support_analytics")
    main()

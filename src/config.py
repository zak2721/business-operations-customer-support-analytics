"""Central project configuration: paths, constants and business rules.

Every module imports paths from here so nothing is hard-coded to a machine.
"""
from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

try:  # optional: load PG credentials etc. from a local .env file
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:  # pragma: no cover
    pass

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
REPORTS_DATA_DIR = DATA_DIR / "reports"
VIS_DIR = PROJECT_ROOT / "visualizations"
REPORTS_DIR = PROJECT_ROOT / "reports"
SQL_DIR = PROJECT_ROOT / "sql"

for _d in (RAW_DIR, PROCESSED_DIR, REPORTS_DATA_DIR, VIS_DIR, REPORTS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

SEED = int(os.getenv("DATA_SEED", "42"))

# ---- Simulation window -----------------------------------------------------
START_DATE = "2023-01-01"
END_DATE = "2025-12-31"           # 3 full years of history
SNAPSHOT_DATE = "2025-12-31 23:59:59"  # "as-of" time for backlog / aging

N_CUSTOMERS = 3_200
N_TICKETS = 24_000
N_AGENTS = 60

# ---- Business rules --------------------------------------------------------
# SLA resolution targets (hours) by priority
SLA_TARGET_HOURS = {"Critical": 8, "High": 24, "Medium": 48, "Low": 72}
# First-response targets (hours) by priority (used for FRT compliance)
FRT_TARGET_HOURS = {"Critical": 1, "High": 4, "Medium": 8, "Low": 24}

TICKET_STATUSES = ["Closed", "Resolved", "Open", "Pending", "In Progress", "Cancelled"]
RESOLVED_STATUSES = {"Closed", "Resolved"}       # have a resolved_date
UNRESOLVED_STATUSES = {"Open", "Pending", "In Progress"}  # backlog
EXCLUDED_STATUSES = {"Cancelled"}                 # excluded from SLA/FCR denominators

SATISFACTION_SCALE = (1, 5)   # CSAT 1..5 ; "satisfied" = 4 or 5
RATING_SCALE = (1, 10)        # customer_rating 1..10 (NPS-style)
CSAT_SATISFIED_THRESHOLD = 4

ACTIVE_RAW_FILES = [
    "customers", "departments", "agents", "support_tickets", "customer_feedback",
    "operations", "agent_performance", "business_costs", "calendar",
]


def pg_dsn() -> dict:
    """Return PostgreSQL connection parameters from environment variables."""
    return {
        "host": os.getenv("PGHOST", "localhost"),
        "port": int(os.getenv("PGPORT", "5432")),
        "dbname": os.getenv("PGDATABASE", "support_analytics"),
        "user": os.getenv("PGUSER", "postgres"),
        "password": os.getenv("PGPASSWORD", ""),
    }

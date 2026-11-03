"""Shared pytest fixtures.

* ``processed`` - the real processed datasets (requires ``python run_pipeline.py`` first).
* ``small_generated`` - a fresh, small dataset generated in memory (fast, independent of disk).
* ``kpi_frame`` - a hand-built ticket table whose KPI answers are known exactly.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import config  # noqa: E402


@pytest.fixture(scope="session")
def processed():
    from src.data_cleaning.loader import load_all_processed
    if not (config.PROCESSED_DIR / "tickets_enriched.csv").exists():
        pytest.skip("processed data missing - run `python run_pipeline.py` first")
    return load_all_processed()


@pytest.fixture(scope="session")
def small_generated():
    from src.data_generation.generate_data import SupportDataGenerator
    return SupportDataGenerator(seed=7, n_customers=400, n_tickets=2500).generate()


@pytest.fixture(scope="session")
def small_cleaned(small_generated):
    from src.data_cleaning.pipeline import add_features, run_cleaning
    clean, log = run_cleaning(small_generated.raw)
    return add_features(clean), log


@pytest.fixture
def kpi_frame() -> pd.DataFrame:
    """Eight tickets with hand-computable KPIs.

    Resolved & eligible: T1..T5 (T6 resolved but invalid timestamp)
    Unresolved: T7 (open), cancelled: T8.
    SLA met: T1 (2h<=8), T2 (20h<=24), T4 (10h<=48)  -> 3 of 5 = 60%
    FCR: T1 only (T3 FCR type but reopened)           -> 1 of 5 = 20%
    """
    t = pd.DataFrame({
        "ticket_id": [f"T{i}" for i in range(1, 9)],
        "customer_id": ["C1", "C1", "C2", "C3", "C3", "C4", "C5", "C6"],
        "agent_id": ["A1", "A1", "A2", "A2", np.nan, "A1", "A2", "A1"],
        "ticket_created_date": pd.to_datetime(["2025-01-01 09:00", "2025-01-03 09:00", "2025-01-05 09:00", "2025-02-01 09:00",
                                               "2025-02-20 09:00", "2025-03-01 09:00", "2025-12-20 09:00", "2025-03-05 09:00"]),
        "ticket_priority": ["Critical", "High", "Medium", "Medium", "Low", "Low", "High", "Low"],
        "sla_target_hours": [8, 24, 48, 48, 72, 72, 24, 72],
        "ticket_status": ["Closed", "Closed", "Resolved", "Closed", "Closed", "Closed", "Open", "Cancelled"],
        "resolution_type": ["First Contact Resolution", "Technical Fix", "First Contact Resolution", "Refund Issued",
                            "Technical Fix", "Technical Fix", None, None],
        "first_response_hours": [1.0, 2.0, 3.0, 4.0, np.nan, 5.0, 6.0, np.nan],
        "resolution_hours": [2.0, 20.0, 60.0, 10.0, 100.0, np.nan, np.nan, np.nan],
        "reopened_count": [0, 0, 1, 0, 0, 0, 0, 0],
        "escalation_flag": [0, 1, 0, 0, 0, 0, 0, 0],
    })
    t["is_resolved"] = t.ticket_status.isin(["Closed", "Resolved"])
    t["is_unresolved"] = t.ticket_status.isin(["Open", "Pending", "In Progress"])
    t["is_cancelled"] = t.ticket_status.eq("Cancelled")
    t["sla_eligible"] = t.is_resolved & t.resolution_hours.notna()
    t["sla_met"] = np.where(t.sla_eligible, t.resolution_hours <= t.sla_target_hours, np.nan)
    t["is_reopened"] = t.reopened_count > 0
    t["is_escalated"] = t.escalation_flag == 1
    t["is_fcr"] = t.sla_eligible & (t.resolution_type == "First Contact Resolution") & ~t.is_reopened & ~t.is_escalated
    t["is_repeat_contact"] = [False, True, False, False, False, False, False, False]
    t["ticket_age_days"] = np.where(t.is_unresolved, 11.5, np.nan)
    t["department_id"] = "DEP-01"
    t["support_channel"] = "Email"
    return t

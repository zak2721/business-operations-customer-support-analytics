"""Data access for the Streamlit app.

``load_dashboard_data`` is a plain function (unit-tested in tests/test_streamlit.py);
``get_data`` wraps it in Streamlit's cache. Customer names are dropped on load:
the app never displays personal information, only IDs and segments.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import config  # noqa: E402
from src.data_cleaning.loader import DataLoadError, load_processed  # noqa: E402

TABLES = ["tickets_enriched", "customer_feedback", "operations", "business_costs", "agent_performance",
          "agents", "departments", "customers"]
PII_COLUMNS = {"customer_name", "customer_comment"}


def load_dashboard_data(processed_dir: Path = config.PROCESSED_DIR) -> dict[str, pd.DataFrame]:
    """Load processed tables, drop PII columns, add department names to operations/costs."""
    data = {}
    for name in TABLES:
        df = load_processed(name, processed_dir)
        data[name] = df.drop(columns=[c for c in df.columns if c in PII_COLUMNS])
    dep = data["departments"][["department_id", "department_name"]]
    data["operations"] = data["operations"].merge(dep, on="department_id", how="left")
    data["business_costs"] = data["business_costs"].merge(dep, on="department_id", how="left")
    data["agent_performance"] = data["agent_performance"].merge(
        data["agents"][["agent_id", "agent_name", "department_id", "experience_level"]], on="agent_id", how="left")
    return data


def load_quality_report(reports_dir: Path = config.REPORTS_DATA_DIR) -> dict:
    """Data-quality outputs written by the cleaning pipeline."""
    out = {"summary": json.loads((reports_dir / "data_quality_summary.json").read_text()),
           "scores": pd.read_csv(reports_dir / "data_quality_scores.csv"),
           "issues": pd.read_csv(reports_dir / "data_quality_issue_log.csv"),
           "profile": pd.read_csv(reports_dir / "column_profile_raw.csv")}
    return out


def get_data() -> dict[str, pd.DataFrame]:
    import streamlit as st

    @st.cache_data(show_spinner="Loading data...")
    def _cached():
        return load_dashboard_data()
    try:
        return _cached()
    except DataLoadError as e:
        st.error(f"{e}\n\nRun `python run_pipeline.py` from the project root, then refresh.")
        st.stop()


def get_quality() -> dict:
    import streamlit as st

    @st.cache_data
    def _cached():
        return load_quality_report()
    return _cached()

"""Streamlit data-loading functions and every page running without exceptions."""
from pathlib import Path

import pandas as pd
import pytest

from streamlit_app.utils.data import PII_COLUMNS, load_dashboard_data, load_quality_report
from streamlit_app.utils.filters import Filters, apply_ticket_filters

APP = Path(__file__).resolve().parents[1] / "streamlit_app"


@pytest.fixture(scope="module")
def dash():
    return load_dashboard_data()


def test_load_dashboard_data_drops_pii(dash):
    for df in dash.values():
        assert not (set(df.columns) & PII_COLUMNS)
    assert "department_name" in dash["operations"] and dash["operations"].department_name.notna().all()


def test_quality_report_loads():
    q = load_quality_report()
    assert {"summary", "scores", "issues", "profile"} <= set(q)
    assert q["summary"]["total_raw_records"] > q["summary"]["total_clean_records"]


def test_apply_ticket_filters(dash):
    t = dash["tickets_enriched"]
    f = Filters(pd.Timestamp("2024-01-01"), pd.Timestamp("2024-03-31"), ["Billing & Accounts"], [], ["Email"], ["High"])
    s = apply_ticket_filters(t, f)
    assert len(s) > 0
    assert s.ticket_created_date.between("2024-01-01", "2024-04-01").all()
    assert set(s.department_name) == {"Billing & Accounts"} and set(s.support_channel) == {"Email"}
    none = Filters(pd.Timestamp("2023-01-01"), pd.Timestamp("2025-12-31"), [], [], [], [])
    assert len(apply_ticket_filters(t, none)) == len(t)


PAGES = ["home.py"] + sorted(p.relative_to(APP).as_posix() for p in (APP / "pages").glob("*.py"))


@pytest.mark.parametrize("page", PAGES)
def test_page_runs_without_exception(page):
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(APP / page), default_timeout=120).run()
    assert not at.exception, [e.value for e in at.exception]


def test_page_reacts_to_filter():
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(APP / "pages/7_SLA_Monitoring.py"), default_timeout=120).run()
    at.sidebar.multiselect(key="f_dep").set_value(["Returns & Refunds"]).run()
    assert not at.exception
    assert any("50.0%" in m.value for m in at.markdown)   # Returns & Refunds SLA compliance

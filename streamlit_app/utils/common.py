"""Page bootstrap shared by all Streamlit pages."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from src.kpi.kpis import KPIFilter, compute_all_kpis  # noqa: E402
from streamlit_app.components.ui import page_setup  # noqa: E402
from streamlit_app.utils.data import get_data  # noqa: E402
from streamlit_app.utils.filters import apply_date_dept, apply_ticket_filters, sidebar_filters  # noqa: E402


def bootstrap(title: str, subtitle: str):
    """Configure the page, render filters, return (data, filters, filtered tickets, kpis)."""
    try:
        st.set_page_config(page_title=f"{title} · Support Analytics", page_icon="📊", layout="wide")
    except Exception:  # already set (e.g. under AppTest)
        pass
    page_setup(title, subtitle)
    d = get_data()
    f = sidebar_filters(d)
    t = apply_ticket_filters(d["tickets_enriched"], f)
    o = apply_date_dept(d["operations"], "operation_date", f)
    c = apply_date_dept(d["business_costs"], "cost_date", f)
    fb = d["customer_feedback"][d["customer_feedback"].ticket_id.isin(t.ticket_id)]
    k = compute_all_kpis(t, fb, o, c, KPIFilter()) if len(t) else {}
    return d, f, t, o, c, k

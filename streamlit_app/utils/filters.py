"""Global sidebar filters shared by every page (kept in st.session_state)."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

PRIORITY_ORDER = ["Critical", "High", "Medium", "Low"]


@dataclass
class Filters:
    start: pd.Timestamp
    end: pd.Timestamp
    departments: list[str]
    segments: list[str]
    channels: list[str]
    priorities: list[str]


def apply_ticket_filters(t: pd.DataFrame, f: Filters) -> pd.DataFrame:
    """Filter the enriched ticket table (pure function - unit tested)."""
    m = (t.ticket_created_date >= f.start) & (t.ticket_created_date < f.end + pd.Timedelta(days=1))
    if f.departments: m &= t.department_name.isin(f.departments)
    if f.segments: m &= t.customer_segment.isin(f.segments)
    if f.channels: m &= t.support_channel.isin(f.channels)
    if f.priorities: m &= t.ticket_priority.isin(f.priorities)
    return t[m]


def apply_date_dept(df: pd.DataFrame, date_col: str, f: Filters) -> pd.DataFrame:
    m = (df[date_col] >= f.start) & (df[date_col] < f.end + pd.Timedelta(days=1))
    if f.departments and "department_name" in df: m &= df.department_name.isin(f.departments)
    return df[m]


def sidebar_filters(data: dict[str, pd.DataFrame]) -> Filters:
    import streamlit as st
    t = data["tickets_enriched"]
    lo, hi = t.ticket_created_date.min().date(), t.ticket_created_date.max().date()
    st.sidebar.markdown("### Filters")
    rng = st.sidebar.date_input("Date range", value=st.session_state.get("f_dates", (lo, hi)), min_value=lo, max_value=hi, key="f_dates")
    start, end = (rng if isinstance(rng, (tuple, list)) and len(rng) == 2 else (lo, hi))
    deps = st.sidebar.multiselect("Department", sorted(t.department_name.unique()), key="f_dep", placeholder="All departments")
    segs = st.sidebar.multiselect("Customer segment", sorted(t.customer_segment.dropna().unique()), key="f_seg", placeholder="All segments")
    chans = st.sidebar.multiselect("Support channel", sorted(t.support_channel.unique()), key="f_chan", placeholder="All channels")
    prios = st.sidebar.multiselect("Ticket priority", PRIORITY_ORDER, key="f_prio", placeholder="All priorities")
    if st.sidebar.button("Reset filters", width="stretch"):
        for k in ("f_dates", "f_dep", "f_seg", "f_chan", "f_prio"):
            st.session_state.pop(k, None)
        st.rerun()
    st.sidebar.caption("Synthetic data · snapshot 31 Dec 2025. Segment/channel/priority filters apply to ticket data; "
                       "operations and cost data respond to date and department.")
    return Filters(pd.Timestamp(start), pd.Timestamp(end), deps, segs, chans, prios)

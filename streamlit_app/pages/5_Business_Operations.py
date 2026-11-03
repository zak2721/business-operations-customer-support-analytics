import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st  # noqa: E402

from src.analytics import eda  # noqa: E402
from src.kpi.kpis import ops_by  # noqa: E402
from src.visualization.theme import STATUS  # noqa: E402
from streamlit_app.components.ui import bar, download, empty_guard, kpi_cards, line  # noqa: E402
from streamlit_app.utils.common import bootstrap  # noqa: E402

d, f, t, o, c, k = bootstrap("Business Operations", "Transaction quality, processing time and operational bottlenecks.")
empty_guard(o)

types = st.multiselect("Operation type", sorted(o.operation_type.unique()), placeholder="All operation types")
procs = st.multiselect("Process", sorted(o.process_name.unique()), placeholder="All processes")
if types: o = o[o.operation_type.isin(types)]
if procs: o = o[o.process_name.isin(procs)]
empty_guard(o)

tot = ops_by(o.assign(all="all"), "all").iloc[0]
kpi_cards([
    ("Total transactions", tot.transactions, "int"), ("Successful", tot.successful, "int"),
    ("Success rate", tot.success_rate_pct, "pct"), ("Failure rate", tot.failure_rate_pct, "pct"),
    ("Operational cost", tot.cost, "usd"), ("Cost per transaction", tot.cost_per_txn, "usd"),
    ("Avg processing time", tot.avg_processing_min, "min"),
])

om = eda.ops_monthly(o)
c1, c2 = st.columns(2)
om["transactions_k"] = om.transactions / 1000
c1.plotly_chart(line(om, "month", ["transactions_k"], "Transactions per month (thousands)", ["Transactions (K)"], ",.0f"), width="stretch")
c2.plotly_chart(line(om, "month", ["failure_rate_pct"], "Failure rate per month (%)", ["Failure rate"], ".2f"), width="stretch")

pr = eda.ops_by_process(o)
c1, c2 = st.columns(2)
c1.plotly_chart(bar(pr, "failure_rate_pct", "process_name", "Failure rate by process (%)", fmt=".2f",
                    color=[STATUS["critical"] if v >= 4 else STATUS["warning"] if v >= 2 else STATUS["good"] for v in pr.sort_values("failure_rate_pct").failure_rate_pct]),
                width="stretch")
c2.plotly_chart(bar(pr, "avg_processing_min", "process_name", "Processing time per transaction (min)", fmt=".2f"), width="stretch")

st.subheader("Bottleneck ranking")
st.caption("Composite percentile score of failure level and trend, processing-time trend, unit-cost trend and share of degraded/critical days (first vs last year in the filter).")
if o.operation_date.dt.year.nunique() >= 2:
    bt = eda.bottleneck_table(o)
    st.dataframe(bt, width="stretch", hide_index=True)
    download(bt, "Bottleneck table (CSV)", "bottlenecks.csv")
else:
    st.info("Select a date range covering at least two years to compare trends.")
st.subheader("Process performance")
st.dataframe(pr, width="stretch", hide_index=True)
download(pr, "Process performance (CSV)", "process_performance.csv")
download(om, "Monthly operations (CSV)", "operations_monthly.csv")

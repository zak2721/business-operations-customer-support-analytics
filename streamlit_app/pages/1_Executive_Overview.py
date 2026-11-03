import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from src.analytics import eda  # noqa: E402
from src.kpi.kpis import kpi_by, ops_by  # noqa: E402
from streamlit_app.components.ui import (bar, download, empty_guard, kpi_cards, line, sla_status,  # noqa: E402
                                         status_colors)
from streamlit_app.utils.common import bootstrap  # noqa: E402

d, f, t, o, c, k = bootstrap("Executive Overview", "Service levels, satisfaction, operational quality and cost at a glance.")
empty_guard(t)

kpi_cards([
    ("Total tickets", k["Total Tickets"], "int"),
    ("Open tickets", k["Open Tickets"], "int", "open · in progress · pending"),
    ("Avg resolution time", k["Avg Resolution Time (h)"], "h", "resolved tickets"),
    ("SLA compliance", k["SLA Compliance Rate (%)"], "pct", "", sla_status(k["SLA Compliance Rate (%)"])),
    ("Customer satisfaction", k["Avg Customer Satisfaction (1-5)"], "csat"),
    ("Operational cost", k["Total Operational Cost ($)"], "usd", "transaction processing"),
    ("Operational success", k["Operational Success Rate (%)"], "pct"),
    ("First contact resolution", k["First Contact Resolution Rate (%)"], "pct"),
])

mk = eda.monthly_ticket_kpis(t)
c1, c2 = st.columns([2, 1])
c1.plotly_chart(line(mk, "month", ["tickets"], "Ticket volume by month", ["Tickets"], ",.0f"), width="stretch")
pr = kpi_by(t, "ticket_priority").set_index("ticket_priority").reindex(eda.PRIORITY_ORDER).dropna(how="all").reset_index()
c2.plotly_chart(bar(pr, "ticket_priority", "tickets", "Tickets by priority", horizontal=False), width="stretch")

c1, c2 = st.columns(2)
c1.plotly_chart(line(mk, "month", ["avg_csat"], "Customer satisfaction trend (1-5)", ["Avg CSAT"], ".2f"), width="stretch")
dep = kpi_by(t, "department_name").sort_values("sla_compliance_pct")
c2.plotly_chart(bar(dep, "sla_compliance_pct", "department_name", "SLA compliance by department (%)", fmt=".1f",
                    color=status_colors(dep.sla_compliance_pct)), width="stretch")

c1, c2 = st.columns(2)
if len(o):
    oy = ops_by(o.assign(year=o.operation_date.dt.year.astype(str)), "year")
    oy_long = pd.concat([oy.assign(outcome="Successful", share=oy.success_rate_pct), oy.assign(outcome="Failed", share=oy.failure_rate_pct)])
    import plotly.express as px
    from streamlit_app.components.ui import style
    from src.visualization.theme import STATUS
    fig = px.bar(oy_long, y="year", x="share", color="outcome", orientation="h",
                 color_discrete_map={"Successful": STATUS["good"], "Failed": STATUS["critical"]})
    fig.update_xaxes(range=[90, 100], ticksuffix="%")
    c1.plotly_chart(style(fig, "Operational success vs failure (% of transactions)"), width="stretch")
    od = ops_by(o, "department_name")
    c2.plotly_chart(bar(od, "cost", "department_name", "Operational cost by department (USD)", fmt="$,.0f"), width="stretch")

st.subheader("Download")
download(pd.DataFrame({"KPI": list(k), "Value": list(k.values())}), "KPI summary (CSV)", "kpi_summary.csv")
download(mk, "Monthly support KPIs (CSV)", "monthly_support_kpis.csv")

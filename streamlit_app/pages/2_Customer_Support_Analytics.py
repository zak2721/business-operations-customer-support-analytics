import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st  # noqa: E402

from src.analytics import eda  # noqa: E402
from src.kpi.kpis import kpi_by  # noqa: E402
from streamlit_app.components.ui import bar, download, empty_guard, heatmap, kpi_cards, line  # noqa: E402
from streamlit_app.utils.common import bootstrap  # noqa: E402

d, f, t, o, c, k = bootstrap("Customer Support Analytics", "Ticket demand, mix, response and resolution performance.")
empty_guard(t)

kpi_cards([
    ("Total tickets", k["Total Tickets"], "int"), ("Resolved", k["Closed Tickets"], "int"),
    ("Open", k["Open Tickets"], "int"), ("Avg first response", k["Avg First Response Time (h)"], "h"),
    ("Median first response", k["Median First Response Time (h)"], "h"),
    ("Avg resolution", k["Avg Resolution Time (h)"], "h"), ("Median resolution", k["Median Resolution Time (h)"], "h"),
    ("First contact resolution", k["First Contact Resolution Rate (%)"], "pct"),
])

cols = ["tickets", "avg_frt_h", "avg_resolution_h", "median_resolution_h", "sla_compliance_pct", "fcr_pct", "escalation_pct", "reopen_pct"]
c1, c2 = st.columns(2)
cat = kpi_by(t, "ticket_category")
c1.plotly_chart(bar(cat, "tickets", "ticket_category", "Tickets by category"), width="stretch")
c2.plotly_chart(bar(cat, "avg_resolution_h", "ticket_category", "Average resolution time by category (h)", fmt=".1f"), width="stretch")

c1, c2, c3 = st.columns(3)
ch = kpi_by(t, "support_channel")
c1.plotly_chart(bar(ch, "tickets", "support_channel", "Tickets by channel"), width="stretch")
c2.plotly_chart(bar(ch, "avg_frt_h", "support_channel", "Avg first response by channel (h)", fmt=".2f"), width="stretch")
st_ = eda.volume_by(t, "ticket_status")
c3.plotly_chart(bar(st_, "tickets", "ticket_status", "Ticket status at snapshot"), width="stretch")

c1, c2 = st.columns(2)
c1.plotly_chart(heatmap(eda.day_hour_matrix(t), "Ticket arrivals by weekday and hour"), width="stretch")
bl = eda.monthly_backlog(t)
c2.plotly_chart(line(bl, "month", ["open_at_month_end"], "Backlog: open tickets at month end", ["Open"], ",.0f"), width="stretch")

c1, c2 = st.columns(2)
c1.plotly_chart(bar(cat, "escalation_pct", "ticket_category", "Escalation rate by category (%)", fmt=".1f"), width="stretch")
c2.plotly_chart(bar(cat, "reopen_pct", "ticket_category", "Reopen rate by category (%)", fmt=".1f"), width="stretch")

st.subheader("KPI breakdown")
dim = st.selectbox("Group by", ["ticket_category", "support_channel", "ticket_priority", "department_name", "customer_segment", "created_year"],
                   format_func=lambda s: s.replace("_", " ").title())
tab = kpi_by(t, dim)[[dim] + cols]
st.dataframe(tab, width="stretch", hide_index=True)
download(tab, f"KPIs by {dim} (CSV)", f"kpis_by_{dim}.csv")

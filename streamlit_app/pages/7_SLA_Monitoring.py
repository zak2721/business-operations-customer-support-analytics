import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st  # noqa: E402

from src.analytics import eda  # noqa: E402
from src.kpi.kpis import kpi_by  # noqa: E402
from streamlit_app.components.ui import bar, download, empty_guard, kpi_cards, line, sla_status, status_colors  # noqa: E402
from streamlit_app.utils.common import bootstrap  # noqa: E402

d, f, t, o, c, k = bootstrap("SLA Monitoring", "Where service targets are missed, and what is aging in the backlog.")
empty_guard(t)

kpi_cards([
    ("SLA compliance", k["SLA Compliance Rate (%)"], "pct", "resolved within target", sla_status(k["SLA Compliance Rate (%)"])),
    ("SLA breach rate", k["SLA Breach Rate (%)"], "pct"), ("Escalated", k["Escalated Tickets"], "int"),
    ("Reopened", k["Reopened Tickets"], "int"), ("Aging backlog >7 days", k["Aging Backlog >7 days"], "int"),
    ("First contact resolution", k["First Contact Resolution Rate (%)"], "pct"),
])

mk = eda.monthly_ticket_kpis(t)
st.plotly_chart(line(mk, "month", ["sla_compliance_pct"], "SLA compliance by creation month (%)", ["SLA %"], ".1f", ref=85, ref_label="Target 85%"),
                width="stretch")

c1, c2, c3 = st.columns(3)
pr = kpi_by(t, "ticket_priority").set_index("ticket_priority").reindex(eda.PRIORITY_ORDER).dropna(how="all").reset_index()
c1.plotly_chart(bar(pr, "ticket_priority", "sla_compliance_pct", "SLA compliance by priority (%)", horizontal=False, fmt=".1f",
                    color=status_colors(pr.sla_compliance_pct)), width="stretch")
dep = kpi_by(t, "department_name").sort_values("sla_compliance_pct")
c2.plotly_chart(bar(dep, "sla_compliance_pct", "department_name", "SLA compliance by department (%)", fmt=".1f",
                    color=status_colors(dep.sla_compliance_pct)), width="stretch")
ag = eda.backlog_aging(t)
c3.plotly_chart(bar(ag, "aging_bucket", "open_tickets", "Open tickets by age", horizontal=False), width="stretch")

st.subheader("Oldest open tickets")
open_t = t[t.is_unresolved.astype(bool)].sort_values("ticket_age_days", ascending=False)
cols = ["ticket_id", "ticket_status", "ticket_priority", "ticket_category", "department_name", "agent_name", "support_channel", "ticket_age_days", "aging_sla_exposed"]
st.dataframe(open_t[cols].head(50), width="stretch", hide_index=True)
download(open_t[cols], "Open ticket list (CSV)", "open_tickets.csv")
st.caption("SLA compliance counts resolved tickets only. Open tickets are tracked here through age and 'past SLA target' exposure.")

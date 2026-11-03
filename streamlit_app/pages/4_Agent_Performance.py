import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import plotly.express as px  # noqa: E402
import streamlit as st  # noqa: E402

from src.analytics import eda  # noqa: E402
from src.visualization.theme import SERIES  # noqa: E402
from streamlit_app.components.ui import bar, download, empty_guard, kpi_cards, sla_status, status_colors, style  # noqa: E402
from streamlit_app.utils.common import bootstrap  # noqa: E402
from streamlit_app.utils.filters import apply_date_dept  # noqa: E402

d, f, t, o, c, k = bootstrap("Agent Performance", "Volume, speed, SLA, quality and satisfaction by agent.")
empty_guard(t)

perf = apply_date_dept(d["agent_performance"].merge(d["departments"][["department_id", "department_name"]], on="department_id"),
                       "performance_date", f)
sc = eda.agent_scorecard(t, perf, d["agents"])
sc = sc[sc.tickets > 0].merge(d["departments"][["department_id", "department_name"]], on="department_id", how="left")
levels = st.multiselect("Experience level", ["Junior", "Mid-Level", "Senior", "Lead"], placeholder="All levels")
teams = st.multiselect("Team", sorted(sc.team.unique()), placeholder="All teams")
if levels: sc = sc[sc.experience_level.isin(levels)]
if teams: sc = sc[sc.team.isin(teams)]
empty_guard(sc)

aht = perf.workload_hours.sum() * 60 / max(perf.tickets_resolved.sum(), 1)
sla = (sc.sla_compliance_pct * sc.resolved).sum() / sc.resolved.sum()
kpi_cards([
    ("Agents", len(sc), "int"), ("Tickets resolved", sc.resolved.sum(), "int"),
    ("Tickets per agent", sc.tickets.mean(), "num"), ("Avg handling time", aht, "num", "minutes, incl. admin"),
    ("Agent SLA compliance", sla, "pct", "resolved-weighted", sla_status(sla)),
    ("Avg agent CSAT", k["Avg Customer Satisfaction (1-5)"], "csat"),
])

c1, c2 = st.columns(2)
c1.plotly_chart(bar(sc.head(15), "resolved", "agent_name", "Top 15 agents by tickets resolved", height=460), width="stretch")
s2 = sc[sc.resolved >= 50]
fig = px.scatter(s2, x="sla_compliance_pct", y="avg_csat", size="tickets", color="experience_level", hover_name="agent_name",
                 color_discrete_sequence=SERIES, category_orders={"experience_level": ["Junior", "Mid-Level", "Senior", "Lead"]},
                 labels={"sla_compliance_pct": "SLA compliance (%)", "avg_csat": "Average CSAT", "experience_level": "Level"})
c2.plotly_chart(style(fig, "SLA compliance vs satisfaction (agents with 50+ resolved)", 460), width="stretch")

c1, c2, c3 = st.columns(3)
slow = s2.sort_values("avg_resolution_h", ascending=False).head(12)
c1.plotly_chart(bar(slow, "avg_resolution_h", "agent_name", "Slowest 12 agents: avg resolution (h)", fmt=".1f"), width="stretch")
ex = eda.experience_level_summary(t[t.agent_id.isin(sc.agent_id)])
ex["experience_level"] = ex.experience_level.astype(str)
c2.plotly_chart(bar(ex, "experience_level", "sla_compliance_pct", "SLA compliance by experience level (%)", horizontal=False,
                    fmt=".1f", color=status_colors(ex.sla_compliance_pct)), width="stretch")
wl = sc.sort_values("tickets_per_active_month", ascending=False).head(12)
c3.plotly_chart(bar(wl, "tickets_per_active_month", "agent_name", "Highest workload (tickets / month)", fmt=".1f"), width="stretch")

st.subheader("Agent scorecard")
cols = ["productivity_rank", "agent_name", "department_name", "team", "experience_level", "employment_status", "tickets", "resolved",
        "resolution_rate_pct", "avg_resolution_h", "sla_compliance_pct", "fcr_pct", "reopen_pct", "avg_csat", "tickets_per_active_month", "aht_minutes"]
st.dataframe(sc[cols], width="stretch", hide_index=True,
             column_config={"sla_compliance_pct": st.column_config.ProgressColumn("SLA %", min_value=0, max_value=100, format="%.1f"),
                            "avg_csat": st.column_config.NumberColumn("CSAT", format="%.2f")})
download(sc[cols], "Agent scorecard (CSV)", "agent_scorecard.csv")

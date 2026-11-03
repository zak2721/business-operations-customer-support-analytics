import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import plotly.express as px  # noqa: E402
import streamlit as st  # noqa: E402

from src.analytics import eda  # noqa: E402
from src.visualization.theme import SERIES  # noqa: E402
from streamlit_app.components.ui import bar, download, empty_guard, kpi_cards, line, style  # noqa: E402
from streamlit_app.utils.common import bootstrap  # noqa: E402

d, f, t, o, c, k = bootstrap("Cost Analysis", "Departmental spend, budget utilisation and unit-cost efficiency.")
empty_guard(c)

kpi_cards([
    ("Departmental cost", k.get("Total Departmental Cost ($)"), "usd", "staffing & overhead"),
    ("Operational cost", k.get("Total Operational Cost ($)"), "usd", "transaction processing"),
    ("Cost per resolved ticket", k.get("Cost per Resolved Ticket ($)"), "usd"),
    ("Cost per transaction", k.get("Avg Cost per Transaction ($)"), "usd"),
    ("Efficiency", k.get("Operational Efficiency (successful txns per $1k)"), "num", "successful txns per $1k"),
])

c1, c2 = st.columns(2)
cd = eda.costs_by(c, "department_name")
c1.plotly_chart(bar(cd, "total", "department_name", "Departmental cost by department (USD)", fmt="$,.0f"), width="stretch")
cc = eda.costs_by(c, "cost_category")
c2.plotly_chart(bar(cc, "total", "cost_category", "Departmental cost by category (USD)", fmt="$,.0f"), width="stretch")

by = eda.costs_yearly_by_department(c, d["departments"])
by["year"] = by.year.astype(str)
fig = px.bar(by, x="department_name", y="budget_utilisation_pct", color="year", barmode="group", color_discrete_sequence=SERIES,
             labels={"budget_utilisation_pct": "% of annual budget", "department_name": ""})
fig.add_hline(y=100, line_dash="dash", line_color="#898781", annotation_text="Budget")
st.plotly_chart(style(fig, "Spend as % of annual budget (full years only are comparable)"), width="stretch")

if len(o):
    om = eda.ops_monthly(o)
    st.plotly_chart(line(om, "month", ["cost_per_txn"], "Cost per transaction by month (USD)", ["Cost / txn"], ".4f"), width="stretch")

st.subheader("Direct vs indirect cost by department")
st.dataframe(cd, width="stretch", hide_index=True)
download(cd, "Costs by department (CSV)", "costs_by_department.csv")
download(by, "Budget utilisation (CSV)", "budget_utilisation.csv")

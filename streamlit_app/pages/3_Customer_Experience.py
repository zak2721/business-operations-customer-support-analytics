import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st  # noqa: E402

from src.analytics import eda  # noqa: E402
from src.kpi.kpis import kpi_by  # noqa: E402
from streamlit_app.components.ui import bar, download, empty_guard, kpi_cards, line  # noqa: E402
from src.visualization.theme import STATUS  # noqa: E402
from streamlit_app.utils.common import bootstrap  # noqa: E402

d, f, t, o, c, k = bootstrap("Customer Experience", "What drives satisfaction - and dissatisfaction.")
empty_guard(t)

kpi_cards([
    ("Avg satisfaction", k["Avg Customer Satisfaction (1-5)"], "csat"),
    ("Satisfied customers", k["Customer Satisfaction Rate (%)"], "pct", "CSAT 4-5"),
    ("Repeat contact rate", k["Customer Repeat Contact Rate (%)"], "pct", "within 7 days"),
    ("Escalation rate", k["Escalation Rate (%)"], "pct"),
])

mk = eda.monthly_ticket_kpis(t)
c1, c2 = st.columns([2, 1])
c1.plotly_chart(line(mk, "month", ["avg_csat"], "Average CSAT by ticket month", ["Avg CSAT"], ".2f"), width="stretch")
ch = kpi_by(t[t.support_channel != "Unknown"], "support_channel")
c2.plotly_chart(bar(ch, "avg_csat", "support_channel", "CSAT by channel", fmt=".2f"), width="stretch")

c1, c2 = st.columns(2)
fb = eda.frt_bucket_csat(t)
fb["frt_bucket"] = fb.frt_bucket.astype(str)
c1.plotly_chart(bar(fb, "frt_bucket", "avg_csat", "CSAT by first response time", horizontal=False, fmt=".2f"), width="stretch")
sm = eda.sla_met_csat(t)
c2.plotly_chart(bar(sm, "sla_outcome", "csat_rate_pct", "% satisfied: SLA met vs breached", horizontal=False, fmt=".1f",
                    color=[STATUS["critical"] if x == "SLA breached" else STATUS["good"] for x in sm.sla_outcome]), width="stretch")

c1, c2, c3 = st.columns(3)
c1.plotly_chart(bar(kpi_by(t, "department_name"), "avg_csat", "department_name", "CSAT by department", fmt=".2f"), width="stretch")
c2.plotly_chart(bar(kpi_by(t, "ticket_category"), "avg_csat", "ticket_category", "CSAT by category", fmt=".2f"), width="stretch")
fcat = eda.feedback_categories(d["customer_feedback"][d["customer_feedback"].ticket_id.isin(t.ticket_id)])
c3.plotly_chart(bar(fcat, "responses", "feedback_category", "Feedback themes (responses)"), width="stretch")

st.subheader("Satisfaction by segment and region")
seg = kpi_by(t, ["customer_segment", "customer_region"])[["customer_segment", "customer_region", "tickets", "avg_csat", "csat_rate_pct", "sla_compliance_pct"]]
st.dataframe(seg, width="stretch", hide_index=True)
download(seg, "Satisfaction by segment & region (CSV)", "csat_by_segment_region.csv")
download(fb, "CSAT by first-response band (CSV)", "csat_by_frt_band.csv")

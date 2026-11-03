"""Home page content (routed from app.py)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st  # noqa: E402

from streamlit_app.components.ui import kpi_cards, sla_status  # noqa: E402
from streamlit_app.utils.common import bootstrap  # noqa: E402

d, f, t, o, c, k = bootstrap("Business Operations & Customer Support Analytics",
                             "End-to-end analytics on 24,000 support tickets, 3,200 customers and 3 years of operations data (synthetic).")

kpi_cards([
    ("Total tickets", k.get("Total Tickets"), "int", "in current filter"),
    ("SLA compliance", k.get("SLA Compliance Rate (%)"), "pct", "resolved within target", sla_status(k.get("SLA Compliance Rate (%)"))),
    ("Avg satisfaction", k.get("Avg Customer Satisfaction (1-5)"), "csat", "valid surveys"),
    ("Operational success", k.get("Operational Success Rate (%)"), "pct", "of transactions"),
])

st.markdown("""
#### What's inside
| Page | Answers |
|---|---|
| **Executive Overview** | How is the operation performing overall? |
| **Customer Support Analytics** | What is driving ticket volume, and how fast are we resolving it? |
| **Customer Experience** | What makes customers satisfied or unhappy? |
| **Agent Performance** | Who is overloaded, who is excelling, where is coaching needed? |
| **Business Operations** | Which processes fail or slow down? |
| **Cost Analysis** | Where does the money go and is it efficient? |
| **SLA Monitoring** | Where are targets missed and what is aging in the backlog? |
| **Data Quality** | How clean is the data and what did cleaning change? |

Use the **filters in the sidebar**; they persist as you move between pages. Every page offers CSV downloads of the tables behind its charts.

KPI definitions follow `docs/KPI_definitions.md` in the repository and match the SQL views and Power BI DAX measures exactly.
""")
st.caption("All data is synthetic and generated for this portfolio project. No real customer information is used or displayed.")

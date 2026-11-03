"""Business Operations & Customer Support Analytics - Streamlit entry point.

Run from the project root:
    streamlit run streamlit_app/app.py

Defines the page navigation; each page lives in its own file under pages/.
"""
from pathlib import Path

import streamlit as st

HERE = Path(__file__).resolve().parent
st.set_page_config(page_title="Support Analytics", page_icon="📊", layout="wide")

PAGES = [
    ("home.py", "Home", "home", "🏠"),
    ("pages/1_Executive_Overview.py", "Executive Overview", "executive-overview", "📈"),
    ("pages/2_Customer_Support_Analytics.py", "Customer Support Analytics", "customer-support", "🎫"),
    ("pages/3_Customer_Experience.py", "Customer Experience", "customer-experience", "💬"),
    ("pages/4_Agent_Performance.py", "Agent Performance", "agent-performance", "🧑‍💼"),
    ("pages/5_Business_Operations.py", "Business Operations", "business-operations", "⚙️"),
    ("pages/6_Cost_Analysis.py", "Cost Analysis", "cost-analysis", "💰"),
    ("pages/7_SLA_Monitoring.py", "SLA Monitoring", "sla-monitoring", "⏱️"),
    ("pages/8_Data_Quality.py", "Data Quality", "data-quality", "🧹"),
]
nav = st.navigation([st.Page(str(HERE / f), title=t, url_path=u, icon=i, default=(u == "home")) for f, t, u, i in PAGES])
nav.run()

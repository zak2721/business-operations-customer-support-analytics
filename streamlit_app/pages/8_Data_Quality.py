import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st  # noqa: E402

from streamlit_app.components.ui import bar, download, kpi_cards, page_setup  # noqa: E402
from streamlit_app.utils.data import get_quality  # noqa: E402

try:
    st.set_page_config(page_title="Data Quality · Support Analytics", page_icon="📊", layout="wide")
except Exception:
    pass
page_setup("Data Quality", "What the cleaning pipeline found, what it changed, and why.")
q = get_quality()
s = q["summary"]
kpi_cards([
    ("Raw records", s["total_raw_records"], "int"), ("Clean records", s["total_clean_records"], "int"),
    ("Removed", s["records_removed"], "int", "exact duplicates & orphans"),
    ("Corrected", s["records_corrected"], "int"), ("Imputed (flagged)", s["records_imputed"], "int"),
    ("Quality score before", s["quality_score_before"], "num", "0-100"), ("Quality score after", s["quality_score_after"], "num", "0-100"),
])
sc = q["scores"]
c1, c2 = st.columns(2)
c1.plotly_chart(bar(sc, "quality_score_before", "table", "Quality score before cleaning", fmt=".2f"), width="stretch")
iss = q["issues"][q["issues"].records_affected > 0]
by_type = iss.groupby("issue_type", as_index=False).records_affected.sum()
c2.plotly_chart(bar(by_type, "records_affected", "issue_type", "Records affected by issue type"), width="stretch")
st.subheader("Cleaning decisions")
st.dataframe(iss, width="stretch", hide_index=True)
st.subheader("Scores by table")
st.dataframe(sc, width="stretch", hide_index=True)
with st.expander("Raw column profile"):
    st.dataframe(q["profile"], width="stretch", hide_index=True)
download(iss, "Issue log (CSV)", "data_quality_issue_log.csv")
download(sc, "Quality scores (CSV)", "data_quality_scores.csv")

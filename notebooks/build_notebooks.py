"""Build and execute the analysis notebooks.

Run from the project root:
    python notebooks/build_notebooks.py

Notebooks are generated from this script (so they stay in sync with the
source modules) and executed with nbconvert, so every output cell is real.
Observations in Markdown cells refer to the default seed (DATA_SEED=42).
"""
from __future__ import annotations

from pathlib import Path

import nbformat as nbf
from nbconvert.preprocessors import ExecutePreprocessor

NB_DIR = Path(__file__).resolve().parent
SETUP = """import sys, warnings
from pathlib import Path
ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
sys.path.insert(0, str(ROOT))
warnings.filterwarnings("ignore")
import pandas as pd, numpy as np
from IPython.display import Image, Markdown, display
pd.set_option("display.max_columns", 30); pd.set_option("display.width", 200); pd.set_option("display.float_format", "{:,.2f}".format)
from src.data_cleaning.loader import load_all_processed, load_all_raw
from src.kpi.kpis import kpi_by, compute_all_kpis
from src.analytics import eda
d = load_all_processed()
t, f, o, c = d["tickets_enriched"], d["customer_feedback"], d["operations"], d["customers"]
VIS = ROOT / "visualizations"
def show(*names):
    for n in names: display(Image(filename=str(VIS / f"{n}.png"), width=820))"""


def md(s): return nbf.v4.new_markdown_cell(s.strip())
def code(s): return nbf.v4.new_code_cell(s.strip())


NOTEBOOKS = {
"01_data_understanding": [
    md("""# 01 · Data Understanding
Structure, volume, keys and relationships of the nine raw datasets *before* cleaning.
> All data is synthetic (Faker + NumPy, seed 42). No real personal data is used."""),
    code(SETUP),
    code("""raw = load_all_raw()
pd.DataFrame({"rows": {k: len(v) for k, v in raw.items()}, "columns": {k: v.shape[1] for k, v in raw.items()}})"""),
    md("## Schema of each raw table"),
    code("""from src.data_validation.validators import profile
prof = pd.concat([profile(v, k) for k, v in raw.items()])
prof[prof.table.isin(["support_tickets", "customers", "customer_feedback"])]"""),
    md("## Sample records"),
    code("""raw["support_tickets"].head(5)"""),
    code("""raw["customers"].head(5)"""),
    md("## Relationships (entity model)\n```\ncustomers 1─* support_tickets *─1 agents *─1 departments\nsupport_tickets 1─0..1 customer_feedback\ndepartments 1─* operations · 1─* business_costs\nagents 1─* agent_performance (monthly)\ncalendar ─ conformed date dimension (2021-2025)\n```"),
    code("""import json
manifest = json.loads((ROOT / "data/raw/_generation_manifest.json").read_text())
pd.Series({k: v for k, v in manifest.items() if isinstance(v, int)}, name="injected defects")"""),
    md("""## Observations
* Tickets cover **Jan 2023 - Dec 2025** (3 years); customers registered from 2021.
* The raw data deliberately contains duplicates, mixed date formats, inconsistent labels, impossible timestamps, out-of-range scores, orphan keys and cost outliers. The manifest above records exactly what was injected so the cleaning stage can be verified against it (see notebook 02 and `tests/test_cleaning.py`)."""),
],
"02_data_cleaning": [
    md("# 02 · Data Cleaning & Quality\nRuns the reusable cleaning pipeline (`src/data_cleaning`) and reviews every decision it logged."),
    code(SETUP),
    code("""from src.data_cleaning.pipeline import run_cleaning, quality_scores
raw = load_all_raw()
clean, log = run_cleaning(raw)
issues = log.to_frame()
issues[issues.records_affected > 0]"""),
    md("## Quality score before vs after"),
    code("""scores = quality_scores(raw, clean, log)
scores[["table", "raw_records", "clean_records", "records_removed", "records_corrected", "records_imputed", "records_flagged", "quality_score_before", "quality_score_after"]]"""),
    md("## Verification: did cleaning catch every injected defect?"),
    code("""m = json.loads((ROOT / "data/raw/_generation_manifest.json").read_text()) if "json" in dir() else __import__("json").loads((ROOT / "data/raw/_generation_manifest.json").read_text())
lk = issues.set_index(["table", "check"]).records_affected
checks = {
 "tickets_exact_duplicates": ("support_tickets", "exact_duplicates"),
 "tickets_resolved_before_created": ("support_tickets", "resolved_before_created"),
 "tickets_orphan_agent": ("support_tickets", "fk_agent"),
 "tickets_wrong_sla_target": ("support_tickets", "sla_target_vs_priority"),
 "feedback_out_of_range_score": ("customer_feedback", "satisfaction_scale"),
 "feedback_orphan_ticket": ("customer_feedback", "fk_ticket"),
 "operations_cost_outliers": ("operations", "cost_outlier_robust_z"),
 "operations_negative_cost": ("operations", "negative_cost"),
 "customers_missing_region": ("customers", "missing_region"),
}
pd.DataFrame([{"defect": k, "injected": m[k], "detected": int(lk[v])} for k, v in checks.items()])"""),
    md("""## Key cleaning decisions
| Issue | Decision | Why |
|---|---|---|
| Exact duplicates | removed | identical rows are copies of the same event |
| Resolved before created | timestamp nulled, ticket kept, flagged | keeps volume KPIs right; excluded from time/SLA KPIs |
| Orphan agent IDs | set to NULL, flagged | ticket still counts; agent KPIs exclude it |
| Wrong SLA target | recomputed from priority | SLA target is a business rule of priority |
| CSAT outside 1-5 | nulled, flagged | cannot be mapped; never imputed |
| Cost outliers (robust z > 8) | replaced by process-month median cost/txn × volume, original kept | 10x+ normal values are entry errors |
| Missing region | derived from country | exact derivation, not an estimate |
| Missing CLV | segment median + `clv_imputed` flag | segments differ ~60x in CLV |

Every injected defect was detected with the exact injected count (table above)."""),
],
"03_exploratory_data_analysis": [
    md("# 03 · Exploratory Data Analysis — customers & demand"),
    code(SETUP),
    code("""k = compute_all_kpis(t, f, o, d["business_costs"])
pd.Series(k, name="value").to_frame()"""),
    md("## Customers"),
    code("""display(eda.customers_by(c, "customer_region")); display(eda.clv_by_segment(c))
show("01_new_customers_by_month", "02_customers_by_region", "03_clv_by_segment")"""),
    md("## Customer activity and repeat contacts"),
    code("""act = eda.customer_activity(t, c)
display(eda.tickets_per_customer_distribution(act))
print(f"7-day repeat contact rate: {t.is_repeat_contact.mean()*100:.1f}%")
show("04_tickets_per_customer", "05_tickets_by_segment")"""),
    md("## Ticket demand patterns"),
    code("""display(eda.volume_by(t, "ticket_category")); display(eda.volume_by(t, "support_channel"))
show("06_ticket_volume_trend", "07_tickets_by_category", "10_tickets_by_channel", "12_day_hour_heatmap")"""),
    md("""## Observations (seed 42)
* Volume grows ~20% from 2023 to 2025 with clear **November-December peaks**.
* **Technical Issue** and **Billing & Payment** are the two largest categories; Billing's share jumps from April 2025.
* Demand is concentrated **Mon-Fri, 09:00-17:00**; weekends carry roughly half the weekday volume.
* Repeat contact is the norm: most contacting customers raise several tickets, and the top 10% of customers raise ~42% of tickets.
* Enterprise customers have a median CLV roughly 60x that of consumers."""),
],
"04_customer_support_analysis": [
    md("# 04 · Customer Support: response, resolution, SLA & satisfaction"),
    code(SETUP),
    code("""cols = ["tickets","avg_frt_h","avg_resolution_h","median_resolution_h","sla_compliance_pct","fcr_pct","escalation_pct","reopen_pct","avg_csat"]
for dim in ["support_channel", "ticket_priority", "department_name", "ticket_category"]:
    display(Markdown(f"### By {dim}")); display(kpi_by(t, dim)[[dim] + cols])"""),
    code("""show("16_frt_by_channel", "17_resolution_by_priority", "18_resolution_by_department", "21_fcr_by_channel", "22_sla_by_department", "23_sla_trend", "24_sla_by_department_year")"""),
    md("## Backlog and aging"),
    code("""display(eda.backlog_aging(t)); display(eda.backlog_by_status_priority(t))
show("15_backlog_trend", "20_backlog_aging")"""),
    md("## Satisfaction"),
    code("""display(eda.frt_bucket_csat(t)); display(eda.sla_met_csat(t)); display(eda.feedback_categories(f))
show("25_csat_trend", "26_csat_by_channel", "27_csat_by_category", "30_csat_vs_first_response", "31_csat_vs_resolution", "32_csat_sla_outcome")"""),
    md("""## Observations (seed 42)
* **Channel is the biggest service divider**: Email/Web Portal/Social answer in hours (≈7-13 h) while Phone/Chat answer in minutes; SLA compliance is ~59-65% vs ~84-86%.
* **Returns & Refunds** is the weakest department (50% SLA, ~60 h average resolution, highest reopen rate).
* **Billing & Accounts** fell from ~83-85% SLA compliance (2023-2024) to ~60% in 2025.
* **Critical** tickets have the *lowest* SLA compliance (~55%) despite top priority.
* CSAT drops monotonically with first response time (4.14 → 2.95), and an SLA breach is associated with a ~1.4 point lower CSAT.
* 60% of the open backlog is older than 30 days: the backlog is stale, not fresh demand."""),
],
"05_agent_performance_analysis": [
    md("# 05 · Agent Performance & Productivity"),
    code(SETUP),
    code("""sc = eda.agent_scorecard(t, d["agent_performance"], d["agents"])
sc[["agent_name","department_id","experience_level","tickets","resolved","resolution_rate_pct","avg_resolution_h","sla_compliance_pct","fcr_pct","reopen_pct","avg_csat","tickets_per_active_month","productivity_rank"]].head(15)"""),
    code("""display(eda.experience_level_summary(t)); display(eda.workload_vs_resolution(d["agent_performance"]))"""),
    code("""show("33_agent_tickets_resolved", "19_resolution_by_agent", "34_agent_sla_vs_csat", "35_agent_workload", "36_experience_level_sla", "37_workload_vs_resolution")"""),
    md("""## Observations (seed 42)
* Experience is the clearest agent-level driver: Junior agents meet SLA on ~53% of tickets vs ~80% for Leads, with ~3x the reopen rate.
* Agent-level SLA compliance and CSAT move together (Spearman ≈ 0.7).
* Workload matters only at the high end: agent-months in the top quintile (≈23 tickets assigned) resolve ~5 h slower and lose ~5 SLA points.
* Billing agents carried the heaviest 2025 load after two departures (see notebook 07)."""),
],
"06_business_operations_analysis": [
    md("# 06 · Business Operations & Cost"),
    code(SETUP),
    code("""display(eda.ops_by_process(o)); display(eda.ops_by_department(o, d["departments"]))"""),
    code("""display(eda.bottleneck_table(o))
show("38_transactions_trend", "39_failure_rate_trend", "40_failure_rate_by_process", "43_processing_time_by_process", "47_bottleneck_score")"""),
    md("## Costs"),
    code("""display(eda.costs_by(d["business_costs"], "cost_category"))
display(eda.costs_yearly_by_department(d["business_costs"], d["departments"]))
display(pd.read_csv(ROOT / "data/reports/rca_ops_cost_decomposition.csv"))
show("41_ops_cost_by_department", "42_ops_cost_by_process", "44_cost_per_transaction_trend", "45_business_costs_by_category", "46_budget_utilisation")"""),
    md("""## Observations (seed 42)
* Overall operational success rate is ~98%, but **Refund Approval** fails ~9% of transactions and worsens every year.
* **Payment Reconciliation** failures nearly doubled after April 2025 — the same month Billing tickets jumped.
* **Shipment Dispatch** slows ~55% in Nov-Dec and is the largest cost line.
* ~80% of operational cost growth is explained by volume; the remainder is rising unit cost, led by Payment Reconciliation.
* All departments overspent their (flat) budgets in 2025; Billing the most (~122%)."""),
],
"07_business_insights": [
    md("# 07 · Advanced Analytics & Business Insights\nStatistical tests, root-cause analysis, an SLA-breach risk model and the resulting insights. **Correlation is not causation**; findings are associations in synthetic data."),
    code(SETUP),
    md("## Correlations (Spearman)"),
    code("""pd.read_csv(ROOT / "data/reports/stats_correlations.csv")"""),
    md("## Chi-square tests of independence"),
    code("""pd.read_csv(ROOT / "data/reports/stats_chi_square.csv")"""),
    md("## Group comparisons (Mann-Whitney U primary, Welch t secondary)"),
    code("""pd.read_csv(ROOT / "data/reports/stats_group_tests.csv")"""),
    md("## 95% confidence intervals"),
    code("""display(pd.read_csv(ROOT / "data/reports/stats_csat_ci_by_channel.csv")); display(pd.read_csv(ROOT / "data/reports/stats_sla_ci_by_department.csv"))"""),
    md("## Regression: drivers of CSAT (OLS, HC3 robust SE) and SLA breach (logit odds ratios)"),
    code("""print((ROOT / "data/reports/stats_csat_regression.txt").read_text()[:2500])"""),
    code("""pd.read_csv(ROOT / "data/reports/stats_sla_logit_odds_ratios.csv", index_col=0)"""),
    md("## Root-cause analysis: where adverse outcomes concentrate"),
    code("""pd.read_csv(ROOT / "data/reports/rca_top_drivers.csv")"""),
    code("""pd.read_csv(ROOT / "data/reports/rca_ops_failure_drivers.csv").head(10)"""),
    md("## Predictive model: SLA-breach risk at ticket creation"),
    code("""m = __import__("json").loads((ROOT / "data/reports/model_metrics.json").read_text())
display(pd.DataFrame(m["models"]).T.drop(columns="confusion_matrix"))
display(pd.read_csv(ROOT / "data/reports/model_risk_deciles.csv"))
print("Excluded (leaky) features:", m["excluded_leaky_features"]); print(m["caveat"])
show("48_model_roc_curve", "49_model_confusion_matrix", "50_model_feature_importance")"""),
    md("## Generated insights"),
    code("""ins = pd.read_json(ROOT / "data/reports/insights.json")
ins[["id","area","priority","title","finding"]]"""),
    md("""## Assumptions & limitations
* Tests assume independent observations; tickets from the same customer/agent are not fully independent, so p-values are optimistic. With n in the thousands, focus on **effect sizes** (Cramer's V, rank-biserial, coefficients) rather than p-values.
* CSAT is ordinal; OLS is an interpretable approximation.
* The model is evaluated on a time-based hold-out and uses creation-time features only; metrics are not evidence of real-world performance because the data is synthetic.
* Full narrative: `reports/business_insights.md` and `reports/recommendations.md`."""),
],
}


def build(execute: bool = True) -> None:
    for name, cells in NOTEBOOKS.items():
        nb = nbf.v4.new_notebook()
        nb["cells"] = cells
        nb["metadata"]["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
        if execute:
            ExecutePreprocessor(timeout=600, kernel_name="python3").preprocess(nb, {"metadata": {"path": str(NB_DIR)}})
        nbf.write(nb, NB_DIR / f"{name}.ipynb")
        print("built", name)


if __name__ == "__main__":
    build()

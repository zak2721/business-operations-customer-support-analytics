"""Generate the Markdown business reports in reports/ from computed results.

Run (after the pipeline and advanced analytics):
    python -m src.analytics.reports
"""
from __future__ import annotations

import json
from datetime import date

import pandas as pd

from src import config
from src.analytics import eda
from src.analytics.insights import build_insights, save_insights
from src.data_cleaning.loader import load_all_processed
from src.kpi.kpis import compute_all_kpis, kpi_by

R = config.REPORTS_DIR
HEADER = ("> **Data notice:** all figures are computed from a synthetic dataset generated for this portfolio project "
          "(seeded, reproducible). They demonstrate the analytical method and are not real company results.\n")


def md_table(df: pd.DataFrame, floatfmt: str = ",.2f") -> str:
    cols = list(df.columns)
    out = ["| " + " | ".join(str(c) for c in cols) + " |", "|" + "|".join("---:" if pd.api.types.is_numeric_dtype(df[c]) else "---" for c in cols) + "|"]
    for row in df.itertuples(index=False):
        out.append("| " + " | ".join(format(v, floatfmt) if isinstance(v, float) else (f"{v:,}" if isinstance(v, int) else str(v)) for v in row) + " |")
    return "\n".join(out)


def fmt_kpi(k: dict) -> pd.DataFrame:
    return pd.DataFrame({"KPI": list(k), "Value": [f"{v:,.2f}" if isinstance(v, float) else f"{v:,}" for v in k.values()]})


def write_all() -> None:
    d = load_all_processed()
    adv = json.loads((config.REPORTS_DATA_DIR / "advanced_results.json").read_text())
    ins = build_insights(d, adv)
    save_insights(ins)
    t, o, c = d["tickets_enriched"], d["operations"], d["business_costs"]
    k = compute_all_kpis(t, d["customer_feedback"], o, c)
    (config.REPORTS_DATA_DIR / "kpi_summary.json").write_text(json.dumps(k, indent=2))
    today = date.today().isoformat()

    # ---------------- business insights
    lines = ["# Business Insights", "", HEADER, f"_Generated {today} by `src/analytics/reports.py`._", "",
             f"{len(ins)} insights. **Finding** and **Evidence** are computed from data; **Hypothesis**, **Action** and "
             "**Expected outcome** are analyst judgement and must be validated before acting.", "",
             "| # | Area | Insight | Priority |", "|---:|---|---|---|"]
    lines += [f"| {i.id} | {i.area} | [{i.title}](#{i.id}-{_anchor(i.title)}) | {i.priority} |" for i in ins]
    for i in ins:
        lines += ["", f"## {i.id}. {i.title}", "", f"**Area:** {i.area} · **Priority:** {i.priority}", "",
                  f"- **Finding (observed):** {i.finding}", f"- **Evidence:** {i.evidence}",
                  f"- **Business impact:** {i.impact}", f"- **Root-cause hypothesis (to validate):** {i.hypothesis}",
                  f"- **Recommended action:** {i.action}", f"- **Expected measurable outcome:** {i.expected_outcome}",
                  f"- **KPI to monitor:** {i.kpi_to_monitor}"]
    (R / "business_insights.md").write_text("\n".join(lines) + "\n")

    # ---------------- recommendations
    rec = ["# Recommendations", "", HEADER, "Prioritised actions derived from the insights. Each links back to its evidence.", ""]
    for pr in ("High", "Medium", "Low"):
        sub = [i for i in ins if i.priority == pr]
        if not sub:
            continue
        rec += [f"## {pr} priority", "", "| # | Action | Owner area | KPI to monitor | Target direction |", "|---:|---|---|---|---|"]
        rec += [f"| {i.id} | {i.action} | {i.area} | {i.kpi_to_monitor} | {i.expected_outcome} |" for i in sub]
        rec.append("")
    rec += ["## 90-day roadmap", "",
            "1. **Weeks 1-4 - stabilise:** backfill Billing capacity, backlog scrub, Critical-incident rota, SLA-at-risk queue.",
            "2. **Weeks 5-8 - fix flow:** Email/Web Portal intake forms and FRT targets, Refund Approval and Payment Reconciliation root-cause reviews.",
            "3. **Weeks 9-12 - institutionalise:** junior-agent routing rules and coaching, seasonal staffing plan, budget re-baseline, breach-risk pilot with control group.",
            "", "Progress is tracked on the Power BI / Streamlit dashboards using the KPIs listed above. No savings figures are claimed: "
            "impact should be measured against the current baselines in `data/reports/kpi_summary.json`."]
    (R / "recommendations.md").write_text("\n".join(rec) + "\n")

    # ---------------- executive summary
    top = [i for i in ins if i.priority == "High"]
    ex = ["# Executive Summary", "", HEADER, f"_Period: Jan 2023 - Dec 2025 · snapshot 31 Dec 2025 · generated {today}_", "",
          "## Headline KPIs", "",
          md_table(fmt_kpi({x: k[x] for x in ["Total Tickets", "Open Tickets", "Avg First Response Time (h)", "Avg Resolution Time (h)",
                                               "SLA Compliance Rate (%)", "First Contact Resolution Rate (%)", "Avg Customer Satisfaction (1-5)",
                                               "Customer Satisfaction Rate (%)", "Operational Success Rate (%)", "Total Operational Cost ($)",
                                               "Avg Cost per Transaction ($)", "Cost per Resolved Ticket ($)"]})), "",
          "## Year over year", "",
          md_table(kpi_by(t, "created_year")[["created_year", "tickets", "avg_frt_h", "avg_resolution_h", "sla_compliance_pct", "fcr_pct", "avg_csat"]]
                   .rename(columns={"created_year": "Year"}).astype({"Year": str})), "",
          "## What needs attention", ""]
    ex += [f"{n}. **{i.title}.** {i.finding}" for n, i in enumerate(top, 1)]
    ex += ["", "## Recommended next steps", ""] + [f"- {i.action}" for i in top[:5]]
    ex += ["", "Full detail: [business_insights.md](business_insights.md) · [recommendations.md](recommendations.md) · "
           "[customer_support_report.md](customer_support_report.md) · [operations_report.md](operations_report.md)"]
    (R / "executive_summary.md").write_text("\n".join(ex) + "\n")

    # ---------------- customer support report
    cols = ["tickets", "avg_frt_h", "avg_resolution_h", "sla_compliance_pct", "fcr_pct", "escalation_pct", "reopen_pct", "avg_csat"]
    cs = ["# Customer Support Performance Report", "", HEADER,
          "Definitions: see [`docs/KPI_definitions.md`](../docs/KPI_definitions.md). Time KPIs are in hours; SLA, FCR and CSAT use resolved-ticket / valid-survey denominators.", ""]
    for title, dim in [("By channel", "support_channel"), ("By priority", "ticket_priority"), ("By department", "department_name"),
                       ("By category", "ticket_category"), ("By agent experience", "experience_level"), ("By customer segment", "customer_segment")]:
        tab = kpi_by(t, dim)[[dim] + cols]
        cs += [f"## {title}", "", md_table(tab), ""]
    cs += ["## Backlog aging (open tickets at snapshot)", "", md_table(eda.backlog_aging(t)), "",
           "## CSAT by first-response band", "", md_table(eda.frt_bucket_csat(t).astype({"frt_bucket": str})), "",
           "## Charts", "", "![SLA by department](../visualizations/22_sla_by_department.png)", "",
           "![CSAT vs FRT](../visualizations/30_csat_vs_first_response.png)", "", "![SLA trend](../visualizations/23_sla_trend.png)", ""]
    sc = eda.agent_scorecard(t, d["agent_performance"], d["agents"])
    cs += ["## Agent scorecard (top 10 by tickets resolved)", "",
           md_table(sc.head(10)[["agent_name", "department_id", "experience_level", "tickets", "resolved", "sla_compliance_pct", "avg_csat", "reopen_pct"]])]
    (R / "customer_support_report.md").write_text("\n".join(cs) + "\n")

    # ---------------- operations report
    ob = eda.ops_by_process(o)
    ops = ["# Business Operations & Cost Report", "", HEADER, "## Operations KPIs", "",
           md_table(fmt_kpi({x: k[x] for x in ["Total Transactions", "Successful Transactions", "Failed Transactions",
                                                "Operational Success Rate (%)", "Operational Failure Rate (%)", "Avg Processing Time (min)",
                                                "Total Operational Cost ($)", "Avg Cost per Transaction ($)",
                                                "Operational Efficiency (successful txns per $1k)", "Total Departmental Cost ($)"]})), "",
           "## By process (sorted by failure rate)", "",
           md_table(ob[["department_id", "process_name", "transactions", "failure_rate_pct", "avg_processing_min", "cost", "cost_per_txn"]]), "",
           "## Bottleneck ranking", "",
           "Composite percentile of 2025 failure rate, failure-rate change, processing-time change, unit-cost change and share of degraded/critical days.", "",
           md_table(eda.bottleneck_table(o)), "",
           "## Cost change decomposition 2023 → 2025 (transaction processing)", "",
           md_table(pd.read_csv(config.REPORTS_DATA_DIR / "rca_ops_cost_decomposition.csv")), "",
           "## Departmental spend vs budget", "",
           md_table(eda.costs_yearly_by_department(c, d["departments"])), "",
           "![Bottlenecks](../visualizations/47_bottleneck_score.png)", "", "![Budget](../visualizations/46_budget_utilisation.png)"]
    (R / "operations_report.md").write_text("\n".join(ops) + "\n")
    print(f"Wrote 5 reports and {len(ins)} insights")


def _anchor(s: str) -> str:
    import re
    return re.sub(r"[^a-z0-9 -]", "", s.lower()).replace(" ", "-")


if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore")
    write_all()

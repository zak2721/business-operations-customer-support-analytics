"""Generate every static EDA chart into visualizations/.

Run:
    python -m src.visualization.generate_charts

Each ``*_charts`` function computes its aggregations through
``src.analytics.eda`` (analysis) and renders them through
``src.visualization.charts`` (presentation), returning {name: path}.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.analytics import eda
from src.data_cleaning.loader import load_all_processed
from src.feature_engineering.features import AGING_LABELS
from src.kpi.kpis import kpi_by
from src.visualization import charts as ch
from src.visualization.theme import SERIES, STATUS

PRI = eda.PRIORITY_ORDER


def customer_charts(d) -> dict[str, Path]:
    c, t = d["customers"], d["tickets_enriched"]
    out = {}
    m = eda.new_customers_by_month(c)
    m = m[m.month >= "2021-01"]
    out["01_new_customers_by_month"] = ch.save(ch.vbar(m, "month", "new_customers", "New customer registrations per month",
        "Customers", "Synthetic customer base, Jan 2021 - Nov 2025", label_every=99, rotate=90, figsize=(12, 4)),
        "01_new_customers_by_month")
    r = eda.customers_by(c, "customer_region")
    out["02_customers_by_region"] = ch.save(ch.hbar(r, "customer_region", "customers", "Customers by region",
        "Customers", f"{len(c):,} customers"), "02_customers_by_region")
    s = eda.clv_by_segment(c)
    out["03_clv_by_segment"] = ch.save(ch.hbar(s, "customer_segment", "median_clv", "Median customer lifetime value by segment",
        "Median CLV (USD)", "Enterprise customers are worth an order of magnitude more than consumers", fmt="$,.0f"),
        "03_clv_by_segment")
    act = eda.customer_activity(t, c)
    dist = eda.tickets_per_customer_distribution(act)
    out["04_tickets_per_customer"] = ch.save(ch.vbar(dist, "tickets_per_customer", "customers",
        "Customers by number of support tickets (2023-2025)", "Customers", "Repeat contact is the norm, not the exception"),
        "04_tickets_per_customer")
    seg = kpi_by(t, "customer_segment")
    out["05_tickets_by_segment"] = ch.save(ch.hbar(seg, "customer_segment", "tickets", "Ticket volume by customer segment",
        "Tickets"), "05_tickets_by_segment")
    return out


def support_charts(d) -> dict[str, Path]:
    t = d["tickets_enriched"]
    out = {}
    mk = eda.monthly_ticket_kpis(t)
    out["06_ticket_volume_trend"] = ch.save(ch.line(mk, "month", "tickets", "Monthly ticket volume",
        "Tickets created", "Steady growth with November-December peaks", fmt=",.0f"), "06_ticket_volume_trend")
    out["07_tickets_by_category"] = ch.save(ch.hbar(eda.volume_by(t, "ticket_category"), "ticket_category", "tickets",
        "Tickets by category", "Tickets", "Technical issues and billing generate the most work"), "07_tickets_by_category")
    pr = eda.volume_by(t, "ticket_priority").set_index("ticket_priority").reindex(PRI).reset_index()
    out["08_tickets_by_priority"] = ch.save(ch.vbar(pr, "ticket_priority", "tickets", "Tickets by priority", "Tickets",
        figsize=(7, 4)), "08_tickets_by_priority")
    out["09_tickets_by_status"] = ch.save(ch.hbar(eda.volume_by(t, "ticket_status"), "ticket_status", "tickets",
        "Ticket status at 31 Dec 2025", "Tickets"), "09_tickets_by_status")
    out["10_tickets_by_channel"] = ch.save(ch.hbar(eda.volume_by(t, "support_channel"), "support_channel", "tickets",
        "Tickets by support channel", "Tickets"), "10_tickets_by_channel")
    out["11_tickets_by_department"] = ch.save(ch.hbar(eda.volume_by(t, "department_name"), "department_name", "tickets",
        "Tickets by department", "Tickets"), "11_tickets_by_department")
    out["12_day_hour_heatmap"] = ch.save(ch.heatmap(eda.day_hour_matrix(t), "When tickets arrive: day of week x hour",
        "Total tickets created 2023-2025 (local time)", xlabel="Hour of day", cbar_label="Tickets"), "12_day_hour_heatmap")
    cat = kpi_by(t, "ticket_category")
    out["13_escalation_by_category"] = ch.save(ch.hbar(cat, "ticket_category", "escalation_pct",
        "Escalation rate by category", "% of non-cancelled tickets escalated", fmt=".1f"), "13_escalation_by_category")
    out["14_reopen_by_category"] = ch.save(ch.hbar(cat, "ticket_category", "reopen_pct", "Reopen rate by category",
        "% of resolved tickets reopened at least once", fmt=".1f"), "14_reopen_by_category")
    bl = eda.monthly_backlog(t)
    out["15_backlog_trend"] = ch.save(ch.line(bl, "month", "open_at_month_end", "Open tickets at month end",
        "Open tickets", "Backlog reconstructed from created / resolved timestamps", fmt=",.0f"), "15_backlog_trend")
    return out


def resolution_charts(d) -> dict[str, Path]:
    t = d["tickets_enriched"]
    out = {}
    ch_k = kpi_by(t[t.support_channel != "Unknown"], "support_channel")
    out["16_frt_by_channel"] = ch.save(ch.hbar(ch_k, "support_channel", "avg_frt_h", "Average first response time by channel",
        "Hours", "Asynchronous channels wait hours; phone and chat are answered in minutes", fmt=".2f"), "16_frt_by_channel")
    e = t[t.sla_eligible.astype(bool)]
    out["17_resolution_by_priority"] = ch.save(ch.boxplot({p: e[e.ticket_priority == p].resolution_hours for p in PRI},
        "Resolution time distribution by priority", "Hours (log scale)", "Box = middle 50% of resolved tickets; dashed = SLA target",
        log=True, ref={"Critical": 8, "High": 24, "Medium": 48, "Low": 72}), "17_resolution_by_priority")
    dep = kpi_by(t, "department_name")
    out["18_resolution_by_department"] = ch.save(ch.hbar(dep, "department_name", "avg_resolution_h",
        "Average resolution time by department", "Hours", fmt=".1f"), "18_resolution_by_department")
    ag = kpi_by(t[t.agent_name.notna()], "agent_name").sort_values("avg_resolution_h")
    sel = pd.concat([ag.head(8), ag.tail(8)])
    out["19_resolution_by_agent"] = ch.save(ch.hbar(sel, "agent_name", "avg_resolution_h",
        "Fastest and slowest 8 agents: average resolution time", "Hours",
        f"Team average {e.resolution_hours.mean():.1f} h", fmt=".1f", ref=e.resolution_hours.mean(), ref_label="avg"),
        "19_resolution_by_agent")
    ag_b = eda.backlog_aging(t)
    out["20_backlog_aging"] = ch.save(ch.vbar(ag_b, "aging_bucket", "open_tickets", "Open ticket backlog by age",
        "Open tickets", "Age at 31 Dec 2025 - most of the backlog is stale, not new", figsize=(8, 4)), "20_backlog_aging")
    out["21_fcr_by_channel"] = ch.save(ch.hbar(ch_k, "support_channel", "fcr_pct", "First contact resolution rate by channel",
        "% of eligible resolved tickets", fmt=".1f"), "21_fcr_by_channel")
    sla = e.groupby("department_name").sla_met.agg(met="sum", n="count").reset_index()
    sla["breached"] = sla.n - sla.met
    out["22_sla_by_department"] = ch.save(ch.two_state_bar(sla, "department_name", "met", "breached",
        "SLA compliance by department", "Resolved tickets, 2023-2025"), "22_sla_by_department")
    mk = eda.monthly_ticket_kpis(t)
    out["23_sla_trend"] = ch.save(ch.line(mk, "month", "sla_compliance_pct", "Monthly SLA compliance",
        "SLA compliance", "Share of resolved tickets closed within target, by creation month", pct=True, ylim=(40, 100)),
        "23_sla_trend")
    x = t.assign(year=t.created_year.astype(str))
    dy = kpi_by(x, ["department_name", "year"])
    out["24_sla_by_department_year"] = ch.save(ch.grouped_bar(dy, "department_name", "year", "sla_compliance_pct",
        "SLA compliance by department and year", "SLA compliance (%)", "Billing & Accounts deteriorated sharply in 2025",
        fmt=".0f", figsize=(12, 4.6)), "24_sla_by_department_year")
    return out


def satisfaction_charts(d) -> dict[str, Path]:
    t, f = d["tickets_enriched"], d["customer_feedback"]
    out = {}
    mk = eda.monthly_ticket_kpis(t)
    out["25_csat_trend"] = ch.save(ch.line(mk, "month", "avg_csat", "Average customer satisfaction by month",
        "CSAT (1-5)", "Surveys linked to tickets created each month", ylim=(3.2, 4.3), fmt=".2f"), "25_csat_trend")
    k = kpi_by(t[t.support_channel != "Unknown"], "support_channel")
    out["26_csat_by_channel"] = ch.save(ch.hbar(k, "support_channel", "avg_csat", "Average CSAT by channel", "CSAT (1-5)",
        fmt=".2f"), "26_csat_by_channel")
    k = kpi_by(t, "ticket_category")
    out["27_csat_by_category"] = ch.save(ch.hbar(k, "ticket_category", "avg_csat", "Average CSAT by ticket category",
        "CSAT (1-5)", fmt=".2f"), "27_csat_by_category")
    k = kpi_by(t, "ticket_priority").set_index("ticket_priority").reindex(PRI).reset_index()
    out["28_csat_by_priority"] = ch.save(ch.vbar(k, "ticket_priority", "avg_csat", "Average CSAT by priority", "CSAT (1-5)",
        fmt=".2f", figsize=(7, 4)), "28_csat_by_priority")
    out["29_feedback_categories"] = ch.save(ch.hbar(eda.feedback_categories(f), "feedback_category", "responses",
        "Customer feedback themes", "Survey responses"), "29_feedback_categories")
    fb = eda.frt_bucket_csat(t)
    out["30_csat_vs_first_response"] = ch.save(ch.vbar(fb, "frt_bucket", "avg_csat",
        "CSAT falls steadily as first response time grows", "Average CSAT (1-5)", "Grouped by first response time",
        fmt=".2f", figsize=(8.5, 4)), "30_csat_vs_first_response")
    rb = eda.resolution_bucket_csat(t)
    out["31_csat_vs_resolution"] = ch.save(ch.vbar(rb, "resolution_bucket", "avg_csat", "CSAT by resolution time",
        "Average CSAT (1-5)", fmt=".2f", figsize=(8.5, 4)), "31_csat_vs_resolution")
    sm = eda.sla_met_csat(t)
    out["32_csat_sla_outcome"] = ch.save(ch.vbar(sm, "sla_outcome", "csat_rate_pct",
        "Satisfied customers (CSAT 4-5): SLA met vs breached", "% satisfied", fmt=".1f",
        color=[STATUS["critical"], STATUS["good"]], figsize=(6.5, 4)), "32_csat_sla_outcome")
    return out


def agent_charts(d) -> dict[str, Path]:
    t, p, a = d["tickets_enriched"], d["agent_performance"], d["agents"]
    out = {}
    sc = eda.agent_scorecard(t, p, a)
    out["33_agent_tickets_resolved"] = ch.save(ch.hbar(sc.head(20), "agent_name", "resolved",
        "Top 20 agents by tickets resolved", "Tickets resolved (2023-2025)"), "33_agent_tickets_resolved")
    s2 = sc.dropna(subset=["sla_compliance_pct", "avg_csat"])
    out["34_agent_sla_vs_csat"] = ch.save(ch.scatter(s2, "sla_compliance_pct", "avg_csat",
        "Agents: SLA compliance vs customer satisfaction", "SLA compliance (%)", "Average CSAT (1-5)",
        "Bubble size = tickets handled; lowest-CSAT agents labelled", size="tickets", label="agent_name", label_top=5),
        "34_agent_sla_vs_csat")
    out["35_agent_workload"] = ch.save(ch.hbar(sc.sort_values("tickets_per_active_month", ascending=False).head(20),
        "agent_name", "tickets_per_active_month", "Highest workload: tickets assigned per active month",
        "Tickets per month", fmt=".1f"), "35_agent_workload")
    ex = eda.experience_level_summary(t)
    out["36_experience_level_sla"] = ch.save(ch.vbar(ex, "experience_level", "sla_compliance_pct",
        "SLA compliance by agent experience level", "SLA compliance (%)", fmt=".1f", figsize=(7.5, 4)),
        "36_experience_level_sla")
    wl = eda.workload_vs_resolution(p)
    out["37_workload_vs_resolution"] = ch.save(ch.vbar(wl, "assigned_bucket", "avg_resolution_h",
        "Resolution time by monthly workload (agent-months)", "Avg resolution time (h)",
        "Quintiles of tickets assigned per agent per month", fmt=".1f", figsize=(8.5, 4)), "37_workload_vs_resolution")
    return out


def operations_charts(d) -> dict[str, Path]:
    o, dep, bc = d["operations"], d["departments"], d["business_costs"]
    out = {}
    om = eda.ops_monthly(o)
    om["transactions_k"] = om.transactions / 1000
    out["38_transactions_trend"] = ch.save(ch.line(om, "month", "transactions_k", "Monthly transaction volume",
        "Transactions (thousands)", fmt=",.0f"), "38_transactions_trend")
    out["39_failure_rate_trend"] = ch.save(ch.line(om, "month", "failure_rate_pct", "Monthly operational failure rate",
        "Failure rate", pct=True, fmt=".2f"), "39_failure_rate_trend")
    pr = eda.ops_by_process(o)
    out["40_failure_rate_by_process"] = ch.save(ch.hbar(pr, "process_name", "failure_rate_pct",
        "Failure rate by process", "% of transactions failed (2023-2025)", fmt=".2f"), "40_failure_rate_by_process")
    od = eda.ops_by_department(o, dep)
    od["cost_m"] = od.cost / 1e6
    out["41_ops_cost_by_department"] = ch.save(ch.hbar(od, "department_name", "cost_m",
        "Transaction processing cost by department", "USD millions (2023-2025)", fmt=",.2f"), "41_ops_cost_by_department")
    pr["cost_m"] = pr.cost / 1e6
    out["42_ops_cost_by_process"] = ch.save(ch.hbar(pr, "process_name", "cost_m", "Transaction processing cost by process",
        "USD millions", fmt=",.2f"), "42_ops_cost_by_process")
    out["43_processing_time_by_process"] = ch.save(ch.hbar(pr, "process_name", "avg_processing_min",
        "Average processing time per transaction", "Minutes (volume-weighted)", fmt=".1f"), "43_processing_time_by_process")
    out["44_cost_per_transaction_trend"] = ch.save(ch.line(om, "month", "cost_per_txn", "Average cost per transaction",
        "USD", fmt=".3f"), "44_cost_per_transaction_trend")
    cc = eda.costs_by(bc, "cost_category")
    cc["total_m"] = cc.total / 1e6
    out["45_business_costs_by_category"] = ch.save(ch.hbar(cc, "cost_category", "total_m",
        "Departmental costs by category", "USD millions (2023-2025)", fmt=",.2f"), "45_business_costs_by_category")
    by = eda.costs_yearly_by_department(bc, dep)
    by["year"] = by.year.astype(str)
    out["46_budget_utilisation"] = ch.save(ch.grouped_bar(by, "department_name", "year", "budget_utilisation_pct",
        "Departmental spend as % of annual budget", "% of budget", "Every department overspent in 2025; Billing the most",
        fmt=".0f", figsize=(12, 4.6)), "46_budget_utilisation")
    bt = eda.bottleneck_table(o)
    out["47_bottleneck_score"] = ch.save(ch.hbar(bt, "process_name", "bottleneck_score", "Operational bottleneck score",
        "Composite percentile score (0-100)",
        "Failure level & trend, processing-time trend, cost trend, degraded days", fmt=".0f"), "47_bottleneck_score")
    return out


def main() -> None:
    d = load_all_processed()
    total = {}
    for fn in (customer_charts, support_charts, resolution_charts, satisfaction_charts, agent_charts, operations_charts):
        total.update(fn(d))
    print(f"{len(total)} charts written to visualizations/")


if __name__ == "__main__":
    main()

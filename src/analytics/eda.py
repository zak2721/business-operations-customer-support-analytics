"""EDA aggregations. Pure functions: DataFrames in, tidy DataFrames out.

Visualization code lives in ``src/visualization``; nothing here plots.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.kpi.kpis import kpi_by, ops_by

PRIORITY_ORDER = ["Critical", "High", "Medium", "Low"]
DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
FRT_BINS = [-0.01, 0.25, 1, 4, 8, 24, 10_000]
FRT_LABELS = ["<15 min", "15-60 min", "1-4 h", "4-8 h", "8-24 h", "24 h+"]


# ---------------------------------------------------------------- customers
def new_customers_by_month(c: pd.DataFrame) -> pd.DataFrame:
    s = c.groupby(c.registration_date.dt.to_period("M")).size()
    return s.rename("new_customers").rename_axis("month").reset_index().assign(month=lambda d: d.month.astype(str))


def customers_by(c: pd.DataFrame, col: str) -> pd.DataFrame:
    return c[col].value_counts().rename_axis(col).reset_index(name="customers")


def clv_by_segment(c: pd.DataFrame) -> pd.DataFrame:
    g = c.groupby("customer_segment").customer_lifetime_value
    return pd.DataFrame({"customers": g.size(), "median_clv": g.median().round(0), "mean_clv": g.mean().round(0),
                         "total_clv": g.sum().round(0)}).sort_values("median_clv", ascending=False).reset_index()


def customer_activity(t: pd.DataFrame, c: pd.DataFrame) -> pd.DataFrame:
    per = t.groupby("customer_id").agg(tickets=("ticket_id", "count"), repeat_contacts=("is_repeat_contact", "sum"))
    out = c.set_index("customer_id")[["customer_segment", "customer_region", "customer_status",
                                      "customer_lifetime_value"]].join(per).fillna({"tickets": 0, "repeat_contacts": 0})
    return out.reset_index()


def tickets_per_customer_distribution(activity: pd.DataFrame) -> pd.DataFrame:
    bins = [-1, 0, 1, 3, 5, 10, 20, 1000]
    labels = ["0", "1", "2-3", "4-5", "6-10", "11-20", "21+"]
    b = pd.cut(activity.tickets, bins, labels=labels)
    return b.value_counts().reindex(labels).rename_axis("tickets_per_customer").reset_index(name="customers")


def status_experience(t: pd.DataFrame, c: pd.DataFrame) -> pd.DataFrame:
    """Average CSAT / SLA experience by customer status (churned vs active)."""
    m = t.merge(c[["customer_id", "customer_status"]], on="customer_id", how="left", suffixes=("", "_c"))
    col = "customer_status_c" if "customer_status_c" in m else "customer_status"
    return kpi_by(m.rename(columns={col: "status"}), "status")[["status", "tickets", "avg_csat", "sla_compliance_pct",
                                                                "reopen_pct", "escalation_pct"]]


# ------------------------------------------------------------------ tickets
def monthly_ticket_kpis(t: pd.DataFrame) -> pd.DataFrame:
    return kpi_by(t, "created_month").rename(columns={"created_month": "month"})


def volume_by(t: pd.DataFrame, col: str) -> pd.DataFrame:
    s = t[col].value_counts()
    out = s.rename_axis(col).reset_index(name="tickets")
    out["share_pct"] = (out.tickets / out.tickets.sum() * 100).round(2)
    return out


def day_hour_matrix(t: pd.DataFrame) -> pd.DataFrame:
    m = t.pivot_table(index="created_dayname", columns="created_hour", values="ticket_id", aggfunc="count", fill_value=0)
    return m.reindex(DAY_ORDER)


def backlog_aging(t: pd.DataFrame) -> pd.DataFrame:
    from src.feature_engineering.features import AGING_LABELS
    u = t[t.is_unresolved.astype(bool)]
    s = u.aging_bucket.value_counts().reindex(AGING_LABELS, fill_value=0)
    return s.rename_axis("aging_bucket").reset_index(name="open_tickets")


def backlog_by_status_priority(t: pd.DataFrame) -> pd.DataFrame:
    u = t[t.is_unresolved.astype(bool)]
    return u.pivot_table(index="ticket_priority", columns="ticket_status", values="ticket_id",
                         aggfunc="count", fill_value=0).reindex(PRIORITY_ORDER)


def monthly_backlog(t: pd.DataFrame) -> pd.DataFrame:
    """Open tickets at each month end, reconstructed from created/resolved timestamps.

    A ticket is open at time T if created <= T and (not resolved by T). Cancelled
    tickets are excluded; tickets resolved with invalid timestamps are treated as
    resolved at creation (they are closed in the system).
    """
    x = t[~t.is_cancelled.astype(bool)]
    ends = pd.date_range(x.ticket_created_date.min().normalize(), "2025-12-31", freq="ME") + pd.Timedelta(hours=23, minutes=59)
    res = x.resolved_date.where(~x.resolution_ts_invalid.astype(bool), x.ticket_created_date)
    rows = [{"month": e.strftime("%Y-%m"),
             "open_at_month_end": int(((x.ticket_created_date <= e) & (res.isna() | (res > e))).sum())} for e in ends]
    return pd.DataFrame(rows)


def frt_bucket_csat(t: pd.DataFrame) -> pd.DataFrame:
    x = t[t.satisfaction_score.notna() & t.first_response_hours.notna()].copy()
    x["frt_bucket"] = pd.cut(x.first_response_hours, FRT_BINS, labels=FRT_LABELS)
    g = x.groupby("frt_bucket", observed=True).satisfaction_score
    return pd.DataFrame({"surveys": g.size(), "avg_csat": g.mean().round(3),
                         "csat_rate_pct": g.apply(lambda s: (s >= 4).mean() * 100).round(2)}).reset_index()


def resolution_bucket_csat(t: pd.DataFrame) -> pd.DataFrame:
    from src.feature_engineering.features import RES_LABELS
    x = t[t.satisfaction_score.notna() & t.resolution_bucket.notna()]
    g = x.groupby("resolution_bucket").satisfaction_score
    out = pd.DataFrame({"surveys": g.size(), "avg_csat": g.mean().round(3)}).reindex(RES_LABELS).dropna()
    return out.reset_index()


def feedback_categories(f: pd.DataFrame) -> pd.DataFrame:
    g = f.groupby("feedback_category").satisfaction_score
    return pd.DataFrame({"responses": g.size(), "avg_csat": g.mean().round(3)}).sort_values("responses", ascending=False).reset_index()


def sla_met_csat(t: pd.DataFrame) -> pd.DataFrame:
    x = t[t.sla_eligible.astype(bool) & t.satisfaction_score.notna()].copy()
    x["sla_outcome"] = np.where(x.sla_met.astype(bool), "Within SLA", "SLA breached")
    g = x.groupby("sla_outcome").satisfaction_score
    return pd.DataFrame({"surveys": g.size(), "avg_csat": g.mean().round(3),
                         "csat_rate_pct": g.apply(lambda s: (s >= 4).mean() * 100).round(2)}).reset_index()


# ------------------------------------------------------------------- agents
def agent_scorecard(t: pd.DataFrame, perf: pd.DataFrame, agents: pd.DataFrame) -> pd.DataFrame:
    k = kpi_by(t[t.agent_id.notna()], "agent_id")
    w = perf.groupby("agent_id").agg(workload_hours=("workload_hours", "sum"), months_active=("performance_id", "count"))
    out = (agents[["agent_id", "agent_name", "department_id", "team", "experience_level", "employment_status"]]
           .merge(k, on="agent_id", how="left").merge(w, on="agent_id", how="left"))
    out["resolution_rate_pct"] = (out.resolved / (out.tickets) * 100).round(2)
    out["tickets_per_active_month"] = (out.tickets / out.months_active).round(1)
    out["aht_minutes"] = (out.workload_hours * 60 / out.resolved).round(1)  # includes admin time share
    out["productivity_rank"] = out.resolved.rank(ascending=False, method="min").astype(int)
    return out.sort_values("resolved", ascending=False).reset_index(drop=True)


def experience_level_summary(t: pd.DataFrame) -> pd.DataFrame:
    order = ["Junior", "Mid-Level", "Senior", "Lead"]
    k = kpi_by(t[t.experience_level.notna()], "experience_level")
    k["experience_level"] = pd.Categorical(k.experience_level, order, ordered=True)
    return k.sort_values("experience_level").reset_index(drop=True)


def workload_vs_resolution(perf: pd.DataFrame) -> pd.DataFrame:
    p = perf.dropna(subset=["average_resolution_time"]).copy()
    p["assigned_bucket"] = pd.qcut(p.tickets_assigned, 5, duplicates="drop")
    g = p.groupby("assigned_bucket", observed=True)
    return pd.DataFrame({"agent_months": g.size(), "avg_assigned": g.tickets_assigned.mean().round(1),
                         "avg_resolution_h": g.average_resolution_time.mean().round(2),
                         "avg_sla_pct": g.sla_compliance_rate.mean().round(2)}).reset_index().assign(
        assigned_bucket=lambda d: d.assigned_bucket.astype(str))


# --------------------------------------------------------------- operations
def ops_monthly(o: pd.DataFrame) -> pd.DataFrame:
    return ops_by(o, "operation_month").rename(columns={"operation_month": "month"})


def ops_by_process(o: pd.DataFrame) -> pd.DataFrame:
    return ops_by(o, ["department_id", "process_name"]).sort_values("failure_rate_pct", ascending=False)


def ops_by_department(o: pd.DataFrame, departments: pd.DataFrame) -> pd.DataFrame:
    out = ops_by(o, "department_id").merge(departments[["department_id", "department_name"]], on="department_id")
    return out.sort_values("cost", ascending=False)


def ops_process_year(o: pd.DataFrame) -> pd.DataFrame:
    x = o.assign(year=o.operation_date.dt.year)
    return ops_by(x, ["process_name", "year"])


def bottleneck_table(o: pd.DataFrame) -> pd.DataFrame:
    """Rank processes on failure rate, processing-time growth, cost growth and incident days."""
    x = o.assign(year=o.operation_date.dt.year)
    y = ops_by(x, ["process_name", "year"])
    first, last = y.year.min(), y.year.max()
    a = y[y.year == first].set_index("process_name")
    b = y[y.year == last].set_index("process_name")
    inc = x.groupby("process_name").operational_status.apply(lambda s: (s != "Normal").mean() * 100)
    out = pd.DataFrame({
        f"failure_rate_{last}": b.failure_rate_pct,
        "failure_rate_change_pp": (b.failure_rate_pct - a.failure_rate_pct).round(2),
        f"avg_processing_min_{last}": b.avg_processing_min,
        "processing_time_change_pct": ((b.avg_processing_min / a.avg_processing_min - 1) * 100).round(1),
        "cost_per_txn_change_pct": ((b.cost_per_txn / a.cost_per_txn - 1) * 100).round(1),
        "degraded_or_critical_days_pct": inc.round(2),
    })
    score = out.rank(pct=True)[[f"failure_rate_{last}", "failure_rate_change_pp", "processing_time_change_pct",
                                "cost_per_txn_change_pct", "degraded_or_critical_days_pct"]].mean(axis=1)
    out["bottleneck_score"] = (score * 100).round(1)
    return out.sort_values("bottleneck_score", ascending=False).reset_index()


def costs_by(costs: pd.DataFrame, col: str) -> pd.DataFrame:
    g = costs.groupby(col)
    return pd.DataFrame({"direct": g.direct_cost.sum(), "indirect": g.indirect_cost.sum(),
                         "total": g.total_cost.sum()}).round(2).sort_values("total", ascending=False).reset_index()


def costs_yearly_by_department(costs: pd.DataFrame, departments: pd.DataFrame) -> pd.DataFrame:
    x = costs.assign(year=costs.cost_date.dt.year).merge(departments[["department_id", "department_name", "operational_budget"]])
    p = x.groupby(["department_name", "year"]).agg(total_cost=("total_cost", "sum"), budget=("operational_budget", "first")).reset_index()
    p["budget_utilisation_pct"] = (p.total_cost / p.budget * 100).round(1)
    return p

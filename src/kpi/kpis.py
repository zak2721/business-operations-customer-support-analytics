"""KPI calculation engine.

Each KPI is a small pure function over processed DataFrames so it can be unit
tested and reused by notebooks, the Streamlit app and report generators.
Definitions (identical in SQL and DAX) are documented in docs/KPI_definitions.md.

Denominator rules
-----------------
* **All-ticket KPIs** (total, open, escalation rate ...) use every non-duplicate ticket.
* **Resolution-rate** = resolved / (all tickets − cancelled).
* **Resolved-ticket KPIs** (avg resolution time, SLA compliance, FCR) use
  ``sla_eligible`` tickets only: status Closed/Resolved *and* a valid
  resolution timestamp. Open, pending, in-progress and cancelled tickets are
  excluded; open tickets are tracked separately by backlog/aging KPIs.
* **FRT KPIs** use tickets that have a first-response timestamp.
* **CSAT KPIs** use surveys with a valid 1-5 score (missing scores never imputed).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src import config


def _safe_div(num: float, den: float) -> float:
    return float(num) / float(den) if den else float("nan")


def _pct(num: float, den: float) -> float:
    return round(_safe_div(num, den) * 100, 2) if den else float("nan")


# ---------------------------------------------------------------- tickets
def total_tickets(t): return int(len(t))
def open_tickets(t): return int(t.is_unresolved.sum())  # Open + In Progress + Pending
def status_count(t, status): return int((t.ticket_status == status).sum())
def closed_tickets(t): return int(t.is_resolved.sum())   # Closed + Resolved
def pending_tickets(t): return status_count(t, "Pending")
def cancelled_tickets(t): return int(t.is_cancelled.sum())
def escalated_tickets(t): return int(t.is_escalated.sum())
def reopened_tickets(t): return int(t.is_reopened.sum())
def ticket_backlog(t): return open_tickets(t)
def aging_backlog(t, days: int = 7): return int((t.is_unresolved & (t.ticket_age_days > days)).sum())


def avg_first_response_hours(t): return round(float(t.first_response_hours.mean()), 2)
def median_first_response_hours(t): return round(float(t.first_response_hours.median()), 2)


def _eligible(t): return t[t.sla_eligible.astype(bool)]


def avg_resolution_hours(t): return round(float(_eligible(t).resolution_hours.mean()), 2)
def median_resolution_hours(t): return round(float(_eligible(t).resolution_hours.median()), 2)


def sla_compliance_rate(t):
    e = _eligible(t)
    return _pct((e.resolution_hours <= e.sla_target_hours).sum(), len(e))


def sla_breach_rate(t):
    e = _eligible(t)
    return _pct((e.resolution_hours > e.sla_target_hours).sum(), len(e))


def fcr_rate(t):
    e = _eligible(t)
    return _pct(e.is_fcr.astype(bool).sum(), len(e))


def resolution_rate(t):
    return _pct(t.is_resolved.sum(), len(t) - t.is_cancelled.sum())


def escalation_rate(t): return _pct(t.is_escalated.sum(), len(t) - t.is_cancelled.sum())
def reopen_rate(t): return _pct(t.is_reopened.sum(), t.is_resolved.sum())


def repeat_contact_rate(t):
    """% of tickets raised within 7 days of the same customer's previous ticket."""
    return _pct(t.is_repeat_contact.astype(bool).sum(), len(t))


def repeat_customer_rate(t):
    """% of contacting customers who raised 2+ tickets in the period."""
    per = t.groupby("customer_id").size()
    return _pct((per >= 2).sum(), len(per))


# --------------------------------------------------------------- feedback
def avg_csat(f): return round(float(f.satisfaction_score.mean()), 3)


def csat_rate(f):
    s = f.satisfaction_score.dropna()
    return _pct((s >= config.CSAT_SATISFIED_THRESHOLD).sum(), len(s))


# ------------------------------------------------------------------ agents
def tickets_per_agent(t):
    a = t.agent_id.dropna()
    return round(_safe_div(len(a), a.nunique()), 1)


def agent_productivity_rate(t):
    """Resolved tickets / assigned (non-cancelled) tickets for tickets with a known agent."""
    a = t[t.agent_id.notna() & ~t.is_cancelled]
    return _pct(a.is_resolved.sum(), len(a))


# -------------------------------------------------------------- operations
def total_transactions(o): return int(o.total_transactions.sum())
def successful_transactions(o): return int(o.successful_transactions.sum())
def failed_transactions(o): return int(o.failed_transactions.sum())
def operational_success_rate(o): return _pct(o.successful_transactions.sum(), o.total_transactions.sum())
def operational_failure_rate(o): return _pct(o.failed_transactions.sum(), o.total_transactions.sum())


def avg_processing_minutes(o):
    """Transaction-weighted average processing time (a simple mean of daily
    averages would over-weight low-volume days)."""
    return round(_safe_div((o.processing_time_minutes * o.total_transactions).sum(), o.total_transactions.sum()), 2)


def total_operational_cost(o): return round(float(o.operational_cost.sum()), 2)
def cost_per_transaction(o): return round(_safe_div(o.operational_cost.sum(), o.total_transactions.sum()), 4)


def operational_efficiency_rate(o):
    """Successful transactions per $1,000 of operational cost (higher is better)."""
    return round(_safe_div(o.successful_transactions.sum(), o.operational_cost.sum()) * 1000, 2)


def cost_per_resolved_ticket(costs, t):
    """Total support-department cost (business_costs) / tickets resolved in the same period."""
    return round(_safe_div(costs.total_cost.sum(), t.is_resolved.sum()), 2)


def departmental_cost(costs) -> pd.Series:
    return costs.groupby("department_id").total_cost.sum().round(2).sort_values(ascending=False)


# ------------------------------------------------------------ orchestration
@dataclass
class KPIFilter:
    start: str | None = None
    end: str | None = None
    departments: list[str] | None = None
    channels: list[str] | None = None
    priorities: list[str] | None = None
    segments: list[str] | None = None
    regions: list[str] | None = None


def filter_tickets(t: pd.DataFrame, flt: KPIFilter) -> pd.DataFrame:
    m = pd.Series(True, index=t.index)
    if flt.start: m &= t.ticket_created_date >= pd.Timestamp(flt.start)
    if flt.end: m &= t.ticket_created_date < pd.Timestamp(flt.end) + pd.Timedelta(days=1)
    if flt.departments: m &= t.department_id.isin(flt.departments) | t.get("department_name", pd.Series(index=t.index)).isin(flt.departments)
    if flt.channels: m &= t.support_channel.isin(flt.channels)
    if flt.priorities: m &= t.ticket_priority.isin(flt.priorities)
    if flt.segments and "customer_segment" in t: m &= t.customer_segment.isin(flt.segments)
    if flt.regions and "customer_region" in t: m &= t.customer_region.isin(flt.regions)
    return t[m]


def filter_by_date(df: pd.DataFrame, col: str, flt: KPIFilter) -> pd.DataFrame:
    m = pd.Series(True, index=df.index)
    if flt.start: m &= df[col] >= pd.Timestamp(flt.start)
    if flt.end: m &= df[col] < pd.Timestamp(flt.end) + pd.Timedelta(days=1)
    if flt.departments and "department_id" in df: m &= df.department_id.isin(flt.departments)
    return df[m]


def compute_all_kpis(tickets: pd.DataFrame, feedback: pd.DataFrame, operations: pd.DataFrame,
                     costs: pd.DataFrame, flt: KPIFilter | None = None) -> dict[str, float]:
    """Return all 30 headline KPIs (plus a few supporting ones) as a dict.

    ``tickets`` should be the processed ticket table (enriched or not). Feedback
    is restricted to surveys for the filtered tickets so CSAT respects ticket
    filters.
    """
    flt = flt or KPIFilter()
    t = filter_tickets(tickets, flt)
    f = feedback[feedback.ticket_id.isin(t.ticket_id)]
    o = filter_by_date(operations, "operation_date", flt)
    c = filter_by_date(costs, "cost_date", flt)
    return {
        # Customer support (1-18)
        "Total Tickets": total_tickets(t),
        "Open Tickets": open_tickets(t),
        "Closed Tickets": closed_tickets(t),
        "Pending Tickets": pending_tickets(t),
        "Escalated Tickets": escalated_tickets(t),
        "Reopened Tickets": reopened_tickets(t),
        "Avg First Response Time (h)": avg_first_response_hours(t),
        "Median First Response Time (h)": median_first_response_hours(t),
        "Avg Resolution Time (h)": avg_resolution_hours(t),
        "First Contact Resolution Rate (%)": fcr_rate(t),
        "Ticket Resolution Rate (%)": resolution_rate(t),
        "SLA Compliance Rate (%)": sla_compliance_rate(t),
        "SLA Breach Rate (%)": sla_breach_rate(t),
        "Ticket Backlog": ticket_backlog(t),
        "Avg Customer Satisfaction (1-5)": avg_csat(f),
        "Customer Satisfaction Rate (%)": csat_rate(f),
        "Tickets per Agent": tickets_per_agent(t),
        "Agent Productivity Rate (%)": agent_productivity_rate(t),
        # Business operations (19-30)
        "Total Transactions": total_transactions(o),
        "Successful Transactions": successful_transactions(o),
        "Failed Transactions": failed_transactions(o),
        "Operational Success Rate (%)": operational_success_rate(o),
        "Operational Failure Rate (%)": operational_failure_rate(o),
        "Avg Processing Time (min)": avg_processing_minutes(o),
        "Total Operational Cost ($)": total_operational_cost(o),
        "Avg Cost per Transaction ($)": cost_per_transaction(o),
        "Cost per Resolved Ticket ($)": cost_per_resolved_ticket(c, t),
        "Total Departmental Cost ($)": round(float(c.total_cost.sum()), 2),
        "Operational Efficiency (successful txns per $1k)": operational_efficiency_rate(o),
        "Customer Repeat Contact Rate (%)": repeat_contact_rate(t),
        # Supporting
        "Median Resolution Time (h)": median_resolution_hours(t),
        "Cancelled Tickets": cancelled_tickets(t),
        "Escalation Rate (%)": escalation_rate(t),
        "Reopen Rate (%)": reopen_rate(t),
        "Aging Backlog >7 days": aging_backlog(t, 7),
        "Repeat Customer Rate (%)": repeat_customer_rate(t),
    }


def kpi_by(t: pd.DataFrame, dim: str | list[str]) -> pd.DataFrame:
    """Core support KPIs grouped by one or more dimensions."""
    def agg(g: pd.DataFrame) -> pd.Series:
        e = g[g.sla_eligible.astype(bool)]
        s = g.satisfaction_score.dropna() if "satisfaction_score" in g else pd.Series(dtype=float)
        return pd.Series({
            "tickets": len(g),
            "resolved": int(g.is_resolved.sum()),
            "open": int(g.is_unresolved.sum()),
            "avg_frt_h": g.first_response_hours.mean(),
            "avg_resolution_h": e.resolution_hours.mean(),
            "median_resolution_h": e.resolution_hours.median(),
            "sla_compliance_pct": _pct((e.resolution_hours <= e.sla_target_hours).sum(), len(e)),
            "fcr_pct": _pct(e.is_fcr.astype(bool).sum(), len(e)),
            "escalation_pct": _pct(g.is_escalated.sum(), len(g) - g.is_cancelled.sum()),
            "reopen_pct": _pct(g.is_reopened.sum(), g.is_resolved.sum()),
            "avg_csat": s.mean() if len(s) else np.nan,
            "csat_rate_pct": _pct((s >= 4).sum(), len(s)) if len(s) else np.nan,
            "surveys": len(s),
        })
    out = t.groupby(dim, observed=True).apply(agg, include_groups=False)
    return out.round(2).reset_index()


def ops_by(o: pd.DataFrame, dim: str | list[str]) -> pd.DataFrame:
    g = o.groupby(dim, observed=True)
    out = pd.DataFrame({
        "transactions": g.total_transactions.sum(),
        "successful": g.successful_transactions.sum(),
        "failed": g.failed_transactions.sum(),
        "cost": g.operational_cost.sum(),
        "proc_minutes_weighted": g.apply(lambda x: (x.processing_time_minutes * x.total_transactions).sum(), include_groups=False),
    })
    out["success_rate_pct"] = (out.successful / out.transactions * 100).round(2)
    out["failure_rate_pct"] = (out.failed / out.transactions * 100).round(2)
    out["cost_per_txn"] = (out.cost / out.transactions).round(4)
    out["avg_processing_min"] = (out.proc_minutes_weighted / out.transactions).round(2)
    return out.drop(columns="proc_minutes_weighted").reset_index()


def main() -> None:
    from src.data_cleaning.loader import load_processed
    import json
    t = load_processed("tickets_enriched")
    k = compute_all_kpis(t, load_processed("customer_feedback"), load_processed("operations"),
                         load_processed("business_costs"))
    (config.REPORTS_DATA_DIR / "kpi_summary.json").write_text(json.dumps(k, indent=2))
    for name, val in k.items():
        print(f"{name:<52} {val:>16,}")


if __name__ == "__main__":
    main()

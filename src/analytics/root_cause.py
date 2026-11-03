"""Root-cause (driver) analysis for adverse outcomes.

Method: for each outcome, compare the outcome rate inside each level of each
candidate factor with the overall rate (``lift``). Factors whose levels show
large lifts on meaningful volume are the drivers to investigate. This is a
descriptive, associational method; it identifies *where* problems
concentrate, not *why* they occur.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

FACTORS = ["ticket_priority", "ticket_category", "support_channel", "department_name", "experience_level",
           "customer_segment", "created_year", "created_dayname"]


def _outcome_frames(t: pd.DataFrame) -> dict[str, tuple[pd.DataFrame, pd.Series]]:
    e = t[t.sla_eligible.astype(bool)].copy()
    p90 = e.resolution_hours.quantile(0.9)
    s = t[t.satisfaction_score.notna()]
    nc = t[~t.is_cancelled.astype(bool)]
    return {
        "SLA breach": (e, e.sla_breached.astype(bool)),
        f"Long resolution (> P90 = {p90:.0f} h)": (e, e.resolution_hours > p90),
        "Low satisfaction (CSAT <= 2)": (s, s.satisfaction_score <= 2),
        "Reopened": (t[t.is_resolved.astype(bool)], t[t.is_resolved.astype(bool)].is_reopened.astype(bool)),
        "Escalated": (nc, nc.is_escalated.astype(bool)),
    }


def driver_table(t: pd.DataFrame, min_n: int = 150) -> pd.DataFrame:
    rows = []
    for outcome, (df, y) in _outcome_frames(t).items():
        base = y.mean()
        for f in FACTORS:
            g = pd.DataFrame({"lvl": df[f], "y": y}).dropna().groupby("lvl").y.agg(["mean", "size", "sum"])
            for lvl, r in g.iterrows():
                if r["size"] < min_n:
                    continue
                rows.append({"outcome": outcome, "factor": f, "level": lvl, "n": int(r["size"]),
                             "outcome_rate_pct": round(r["mean"] * 100, 2), "baseline_pct": round(base * 100, 2),
                             "lift": round(r["mean"] / base, 2), "excess_cases": int(r["sum"] - base * r["size"])})
    return pd.DataFrame(rows)


def top_drivers(dt: pd.DataFrame, k: int = 5) -> pd.DataFrame:
    """Top levels by excess cases (volume-weighted impact) per outcome."""
    return (dt[dt.lift > 1].sort_values(["outcome", "excess_cases"], ascending=[True, False])
            .groupby("outcome").head(k).reset_index(drop=True))


def factor_spread(dt: pd.DataFrame) -> pd.DataFrame:
    """For each outcome x factor, the spread between best and worst level (pp).
    A larger spread means the factor discriminates the outcome more."""
    g = dt.groupby(["outcome", "factor"]).outcome_rate_pct
    out = (g.max() - g.min()).rename("spread_pp").reset_index()
    return out.sort_values(["outcome", "spread_pp"], ascending=[True, False])


def ops_failure_drivers(o: pd.DataFrame) -> pd.DataFrame:
    x = o.assign(year=o.operation_date.dt.year, q4=o.operation_date.dt.month.isin([11, 12]),
                 weekend=o.operation_date.dt.dayofweek >= 5)
    rows = []
    base = x.failed_transactions.sum() / x.total_transactions.sum()
    for f in ["process_name", "operation_type", "department_id", "year", "q4", "weekend"]:
        g = x.groupby(f)[["failed_transactions", "total_transactions"]].sum()
        for lvl, r in g.iterrows():
            rate = r.failed_transactions / r.total_transactions
            rows.append({"factor": f, "level": lvl, "transactions": int(r.total_transactions),
                         "failure_rate_pct": round(rate * 100, 3), "lift": round(rate / base, 2),
                         "excess_failures": int(r.failed_transactions - base * r.total_transactions)})
    return pd.DataFrame(rows).sort_values("excess_failures", ascending=False)


def cost_change_decomposition(o: pd.DataFrame, y0: int = 2023, y1: int = 2025) -> pd.DataFrame:
    """Split each process's operational cost change into a volume effect and a
    unit-cost (price) effect: dC = (V1-V0)*P0 + (P1-P0)*V1."""
    x = o.assign(year=o.operation_date.dt.year)
    g = x[x.year.isin([y0, y1])].groupby(["process_name", "year"])[["operational_cost", "total_transactions"]].sum().unstack()
    c0, c1 = g.operational_cost[y0], g.operational_cost[y1]
    v0, v1 = g.total_transactions[y0], g.total_transactions[y1]
    p0, p1 = c0 / v0, c1 / v1
    out = pd.DataFrame({f"cost_{y0}": c0.round(0), f"cost_{y1}": c1.round(0), "cost_change": (c1 - c0).round(0),
                        "cost_change_pct": ((c1 / c0 - 1) * 100).round(1), "volume_effect": ((v1 - v0) * p0).round(0),
                        "unit_cost_effect": ((p1 - p0) * v1).round(0),
                        "unit_cost_change_pct": ((p1 / p0 - 1) * 100).round(1)})
    return out.sort_values("unit_cost_effect", ascending=False).reset_index()


def business_cost_growth(costs: pd.DataFrame, departments: pd.DataFrame, y0: int = 2023, y1: int = 2025) -> pd.DataFrame:
    x = costs.assign(year=costs.cost_date.dt.year).merge(departments[["department_id", "department_name"]])
    g = x[x.year.isin([y0, y1])].groupby(["department_name", "cost_category", "year"]).total_cost.sum().unstack()
    g["change"] = (g[y1] - g[y0]).round(0)
    g["change_pct"] = ((g[y1] / g[y0] - 1) * 100).round(1)
    return g.reset_index().sort_values("change", ascending=False)

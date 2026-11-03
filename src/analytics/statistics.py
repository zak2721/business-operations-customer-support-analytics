"""Statistical analysis: descriptive stats, correlation, hypothesis tests, CIs, regression.

Assumptions and limitations are documented next to each test and summarised
in ``docs/methodology.md``. Correlation results never imply causation.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats


def descriptive(t: pd.DataFrame, o: pd.DataFrame) -> pd.DataFrame:
    e = t[t.sla_eligible.astype(bool)]
    series = {
        "first_response_hours": t.first_response_hours,
        "resolution_hours (resolved)": e.resolution_hours,
        "satisfaction_score": t.satisfaction_score,
        "customer_rating": t.customer_rating,
        "daily_process_cost_usd": o.operational_cost,
        "processing_time_minutes": o.processing_time_minutes,
    }
    rows = []
    for k, s in series.items():
        s = s.dropna()
        rows.append({"metric": k, "n": len(s), "mean": s.mean(), "std": s.std(), "min": s.min(),
                     "p25": s.quantile(.25), "median": s.median(), "p75": s.quantile(.75), "p90": s.quantile(.9),
                     "max": s.max(), "skew": stats.skew(s)})
    return pd.DataFrame(rows).round(3)


def mean_ci(s: pd.Series, conf: float = 0.95) -> tuple[float, float, float, int]:
    """Mean and t-distribution confidence interval."""
    s = s.dropna()
    m, se = s.mean(), stats.sem(s)
    h = se * stats.t.ppf((1 + conf) / 2, len(s) - 1)
    return m, m - h, m + h, len(s)


def proportion_ci(k: int, n: int, conf: float = 0.95) -> tuple[float, float, float]:
    """Wilson score interval for a proportion (better than normal approx near 0/1)."""
    z = stats.norm.ppf((1 + conf) / 2)
    p = k / n
    den = 1 + z ** 2 / n
    centre = (p + z ** 2 / (2 * n)) / den
    half = z * np.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / den
    return p * 100, (centre - half) * 100, (centre + half) * 100


def csat_ci_by(t: pd.DataFrame, dim: str) -> pd.DataFrame:
    rows = []
    for k, g in t.groupby(dim):
        m, lo, hi, n = mean_ci(g.satisfaction_score)
        rows.append({dim: k, "n_surveys": n, "avg_csat": m, "ci95_low": lo, "ci95_high": hi})
    return pd.DataFrame(rows).round(3).sort_values("avg_csat", ascending=False)


def sla_ci_by(t: pd.DataFrame, dim: str) -> pd.DataFrame:
    e = t[t.sla_eligible.astype(bool)]
    rows = []
    for k, g in e.groupby(dim):
        p, lo, hi = proportion_ci(int(g.sla_met.sum()), len(g))
        rows.append({dim: k, "n_resolved": len(g), "sla_pct": p, "ci95_low": lo, "ci95_high": hi})
    return pd.DataFrame(rows).round(2).sort_values("sla_pct")


def correlations(t: pd.DataFrame, perf: pd.DataFrame, o: pd.DataFrame) -> pd.DataFrame:
    """Spearman (rank) correlations - robust to the heavy right skew of time metrics."""
    rows = []

    def add(name, x, y, note):
        d = pd.concat([x, y], axis=1).dropna()
        rho, p = stats.spearmanr(d.iloc[:, 0], d.iloc[:, 1])
        r, pp = stats.pearsonr(d.iloc[:, 0], d.iloc[:, 1])
        rows.append({"relationship": name, "n": len(d), "spearman_rho": round(rho, 3), "spearman_p": p,
                     "pearson_r": round(r, 3), "pearson_p": pp, "unit": note})

    add("First response time vs CSAT", t.first_response_hours, t.satisfaction_score, "ticket")
    add("Resolution time vs CSAT", t.resolution_hours.where(t.sla_eligible.astype(bool)), t.satisfaction_score, "ticket")
    add("Agent monthly workload vs avg resolution time", perf.tickets_assigned, perf.average_resolution_time, "agent-month")
    add("Agent monthly workload vs SLA compliance", perf.tickets_assigned, perf.sla_compliance_rate, "agent-month")
    pr = t.ticket_priority.map({"Critical": 4, "High": 3, "Medium": 2, "Low": 1})
    add("Priority (ordinal) vs SLA breach", pr.where(t.sla_eligible.astype(bool)), t.sla_breached, "ticket")
    daily = o.groupby("operation_date").agg(cost=("operational_cost", "sum"), txns=("total_transactions", "sum"))
    add("Daily transaction volume vs operational cost", daily.txns, daily.cost, "day")
    out = pd.DataFrame(rows)
    out["strength"] = pd.cut(out.spearman_rho.abs(), [0, .1, .3, .5, 1.01], labels=["negligible", "weak", "moderate", "strong"])
    return out


def cramers_v(ct: pd.DataFrame) -> float:
    chi2 = stats.chi2_contingency(ct)[0]
    n = ct.values.sum()
    r, k = ct.shape
    return float(np.sqrt(chi2 / (n * (min(r, k) - 1))))


def chi_square_tests(t: pd.DataFrame) -> pd.DataFrame:
    e = t[t.sla_eligible.astype(bool)]
    s = t[t.satisfaction_score.notna()]
    tests = {
        "Priority x SLA breach": pd.crosstab(e.ticket_priority, e.sla_breached),
        "Channel x SLA breach": pd.crosstab(e.support_channel, e.sla_breached),
        "Category x SLA breach": pd.crosstab(e.ticket_category, e.sla_breached),
        "Channel x Satisfied (CSAT>=4)": pd.crosstab(s.support_channel, s.satisfaction_score >= 4),
        "Experience level x Reopened": pd.crosstab(t.experience_level, t.is_reopened),
        "Customer segment x SLA breach": pd.crosstab(e.customer_segment, e.sla_breached),
    }
    rows = []
    for name, ct in tests.items():
        chi2, p, dof, exp = stats.chi2_contingency(ct)
        rows.append({"test": name, "chi2": round(chi2, 2), "dof": dof, "p_value": p, "cramers_v": round(cramers_v(ct), 3),
                     "min_expected_count": round(exp.min(), 1), "significant_at_0.05": p < 0.05})
    return pd.DataFrame(rows)


def group_difference_tests(t: pd.DataFrame) -> pd.DataFrame:
    """Two-group comparisons. Mann-Whitney U (no normality assumption) is the
    primary test; Welch's t-test (unequal variances) is reported alongside."""
    e = t[t.sla_eligible.astype(bool)]
    cases = [
        ("CSAT: within SLA vs breached", t[t.sla_met == 1].satisfaction_score, t[t.sla_met == 0].satisfaction_score),
        ("Resolution h: Junior vs Senior/Lead agents", e[e.experience_level == "Junior"].resolution_hours,
         e[e.experience_level.isin(["Senior", "Lead"])].resolution_hours),
        ("CSAT: real-time (phone/chat) vs async channels",
         t[t.support_channel.isin(["Phone", "Live Chat"])].satisfaction_score,
         t[t.support_channel.isin(["Email", "Web Portal", "Social Media"])].satisfaction_score),
        ("CSAT: FCR vs non-FCR resolved tickets", e[e.is_fcr.astype(bool)].satisfaction_score,
         e[~e.is_fcr.astype(bool)].satisfaction_score),
        ("Resolution h: Billing 2025 vs Billing 2024",
         e[(e.department_name == "Billing & Accounts") & (e.created_year == 2025)].resolution_hours,
         e[(e.department_name == "Billing & Accounts") & (e.created_year == 2024)].resolution_hours),
    ]
    rows = []
    for name, a, b in cases:
        a, b = a.dropna(), b.dropna()
        u, pu = stats.mannwhitneyu(a, b, alternative="two-sided")
        tt, pt = stats.ttest_ind(a, b, equal_var=False)
        rbc = 1 - 2 * u / (len(a) * len(b))      # rank-biserial effect size
        rows.append({"comparison": name, "n_a": len(a), "n_b": len(b), "mean_a": round(a.mean(), 3),
                     "mean_b": round(b.mean(), 3), "median_a": round(a.median(), 3), "median_b": round(b.median(), 3),
                     "mann_whitney_p": pu, "welch_t_p": pt, "rank_biserial": round(-rbc, 3)})
    kw = stats.kruskal(*[g.resolution_hours.dropna() for _, g in e.groupby("support_channel")])
    rows.append({"comparison": "Resolution h across 6 channels (Kruskal-Wallis)", "n_a": len(e), "n_b": np.nan,
                 "mean_a": np.nan, "mean_b": np.nan, "median_a": np.nan, "median_b": np.nan,
                 "mann_whitney_p": kw.pvalue, "welch_t_p": np.nan, "rank_biserial": np.nan})
    return pd.DataFrame(rows)


def two_proportion_test(k1: int, n1: int, k2: int, n2: int) -> dict:
    p1, p2 = k1 / n1, k2 / n2
    p = (k1 + k2) / (n1 + n2)
    z = (p1 - p2) / np.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    return {"p1_pct": round(p1 * 100, 2), "p2_pct": round(p2 * 100, 2), "diff_pp": round((p1 - p2) * 100, 2),
            "z": round(z, 3), "p_value": 2 * (1 - stats.norm.cdf(abs(z)))}


def billing_sla_test(t: pd.DataFrame) -> dict:
    e = t[t.sla_eligible.astype(bool) & (t.department_name == "Billing & Accounts")]
    a, b = e[e.created_year == 2025], e[e.created_year == 2024]
    return two_proportion_test(int(a.sla_met.sum()), len(a), int(b.sla_met.sum()), len(b))


def csat_regression(t: pd.DataFrame):
    """OLS of CSAT on service-experience factors (ticket level).

    CSAT is ordinal (1-5); OLS is used as an interpretable approximation, with
    HC3 robust standard errors. Coefficients are associations, not causal effects.
    """
    d = t[t.satisfaction_score.notna() & t.sla_eligible.astype(bool) & t.first_response_hours.notna()].copy()
    d["log_frt"] = np.log1p(d.first_response_hours)
    d["sla_breached_i"] = d.sla_breached.astype(int)
    d["escalated"] = d.escalation_flag
    d["fcr"] = d.is_fcr.astype(int)
    d = d[d.support_channel != "Unknown"]
    m = smf.ols("satisfaction_score ~ log_frt + sla_breached_i + reopened_count + escalated + fcr"
                " + C(support_channel, Treatment('Email')) + C(ticket_category, Treatment('Product Inquiry'))", data=d)
    return m.fit(cov_type="HC3")


def sla_logit(t: pd.DataFrame):
    """Logistic regression of SLA breach on ticket attributes known at creation (odds ratios)."""
    d = t[t.sla_eligible.astype(bool) & t.experience_level.notna() & (t.support_channel != "Unknown")].copy()
    d["breach"] = d.sla_breached.astype(int)
    d["q4"] = d.ticket_created_date.dt.month.isin([11, 12]).astype(int)
    m = smf.logit("breach ~ C(ticket_priority, Treatment('Low')) + C(support_channel, Treatment('Phone'))"
                  " + C(ticket_category, Treatment('Product Inquiry')) + C(experience_level, Treatment('Lead')) + q4",
                  data=d).fit(disp=False)
    or_ = pd.DataFrame({"odds_ratio": np.exp(m.params), "ci_low": np.exp(m.conf_int()[0]),
                        "ci_high": np.exp(m.conf_int()[1]), "p_value": m.pvalues}).round(4)
    return m, or_

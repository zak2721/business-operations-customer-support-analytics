"""Run statistical, root-cause and predictive analysis; persist every result.

Run:
    python -m src.analytics.run_advanced

Outputs (data/reports/): stats_*.csv, rca_*.csv, model_*.{json,csv},
advanced_results.json (compact numbers consumed by the insight generator).
"""
from __future__ import annotations

import json

import pandas as pd

from src import config
from src.analytics import predictive, root_cause as rc, statistics as st
from src.data_cleaning.loader import load_processed

OUT = config.REPORTS_DATA_DIR


def run() -> dict:
    t = load_processed("tickets_enriched")
    o = load_processed("operations")
    p = load_processed("agent_performance")
    c = load_processed("business_costs")
    d = load_processed("departments")

    st.descriptive(t, o).to_csv(OUT / "stats_descriptive.csv", index=False)
    corr = st.correlations(t, p, o); corr.to_csv(OUT / "stats_correlations.csv", index=False)
    chi = st.chi_square_tests(t); chi.to_csv(OUT / "stats_chi_square.csv", index=False)
    grp = st.group_difference_tests(t); grp.to_csv(OUT / "stats_group_tests.csv", index=False)
    st.csat_ci_by(t[t.support_channel != "Unknown"], "support_channel").to_csv(OUT / "stats_csat_ci_by_channel.csv", index=False)
    st.sla_ci_by(t, "department_name").to_csv(OUT / "stats_sla_ci_by_department.csv", index=False)
    bill = st.billing_sla_test(t)
    ols = st.csat_regression(t)
    (OUT / "stats_csat_regression.txt").write_text(str(ols.summary()))
    ols_tab = pd.DataFrame({"coef": ols.params, "ci_low": ols.conf_int()[0], "ci_high": ols.conf_int()[1],
                            "p_value": ols.pvalues}).round(4)
    ols_tab.to_csv(OUT / "stats_csat_regression_coefficients.csv")
    logit, odds = st.sla_logit(t)
    odds.to_csv(OUT / "stats_sla_logit_odds_ratios.csv")

    dt = rc.driver_table(t); dt.to_csv(OUT / "rca_driver_table.csv", index=False)
    rc.top_drivers(dt).to_csv(OUT / "rca_top_drivers.csv", index=False)
    rc.factor_spread(dt).to_csv(OUT / "rca_factor_spread.csv", index=False)
    of = rc.ops_failure_drivers(o); of.to_csv(OUT / "rca_ops_failure_drivers.csv", index=False)
    cd = rc.cost_change_decomposition(o); cd.to_csv(OUT / "rca_ops_cost_decomposition.csv", index=False)
    bg = rc.business_cost_growth(c, d); bg.to_csv(OUT / "rca_business_cost_growth.csv", index=False)

    model = predictive.train_and_evaluate(t)

    results = {
        "correlations": corr.set_index("relationship")[["n", "spearman_rho", "spearman_p", "strength"]].astype(str).to_dict("index"),
        "chi_square": chi.set_index("test")[["chi2", "p_value", "cramers_v"]].to_dict("index"),
        "group_tests": grp.set_index("comparison").to_dict("index"),
        "billing_sla_2025_vs_2024": bill,
        "csat_ols_r2": round(float(ols.rsquared), 4),
        "csat_ols_key_coefs": ols_tab.loc[["log_frt", "sla_breached_i", "reopened_count", "escalated", "fcr"]].to_dict("index"),
        "sla_logit_pseudo_r2": round(float(logit.prsquared), 4),
        "model": {k: model[k] for k in ("selected_model", "models", "top_decile_breach_rate_pct",
                                        "bottom_decile_breach_rate_pct", "test_breach_rate_pct", "top_features")},
    }
    (OUT / "advanced_results.json").write_text(json.dumps(results, indent=2, default=str))
    return results


if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore")
    r = run()
    print(json.dumps({k: r[k] for k in ("billing_sla_2025_vs_2024", "csat_ols_r2", "csat_ols_key_coefs")}, indent=2))

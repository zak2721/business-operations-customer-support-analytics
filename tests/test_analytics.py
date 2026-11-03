"""Advanced analytics outputs, model leakage controls and insight generation."""
import json

import pandas as pd

from src import config
from src.analytics import predictive


def test_insights_are_generated_from_data():
    ins = json.loads((config.REPORTS_DATA_DIR / "insights.json").read_text())
    assert len(ins) >= 20
    required = {"finding", "evidence", "impact", "hypothesis", "action", "expected_outcome", "kpi_to_monitor"}
    assert all(required <= set(i) and all(i[k] for k in required) for i in ins)
    kpi = json.loads((config.REPORTS_DATA_DIR / "kpi_summary.json").read_text())
    # the company SLA figure quoted in insight text matches the KPI engine
    assert any(f"company {kpi['SLA Compliance Rate (%)']:.1f}%" in i["finding"] for i in ins)


def test_model_uses_no_leaky_features():
    assert not set(predictive.LEAKY) & set(predictive.CAT + predictive.NUM)


def test_model_time_split_and_metrics():
    m = json.loads((config.REPORTS_DATA_DIR / "model_metrics.json").read_text())
    assert m["train_period"].endswith("2024-12-31") and m["test_period"].startswith("2025-01-01")
    for res in m["models"].values():
        assert 0.5 < res["test_roc_auc"] <= 1
        cm = res["confusion_matrix"]
        assert sum(cm.values()) == m["test_rows"]


def test_agent_load_feature_uses_only_past(processed):
    t = processed["tickets_enriched"]
    f = predictive.build_features(t)
    a = f[f.agent_id == f.agent_id.iloc[0]].sort_values("ticket_created_date").iloc[50]
    allt = t[(t.agent_id == a.agent_id) & (t.ticket_created_date < a.ticket_created_date)
             & (t.ticket_created_date >= a.ticket_created_date - pd.Timedelta(days=7))]
    assert a.agent_load_7d == len(allt)


def test_statistical_outputs_exist():
    for f in ("stats_correlations.csv", "stats_chi_square.csv", "stats_group_tests.csv", "stats_csat_regression.txt",
              "rca_driver_table.csv", "rca_ops_cost_decomposition.csv"):
        assert (config.REPORTS_DATA_DIR / f).exists(), f
    corr = pd.read_csv(config.REPORTS_DATA_DIR / "stats_correlations.csv")
    assert corr.spearman_rho.between(-1, 1).all()

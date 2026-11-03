"""Optional predictive model: flag tickets at risk of breaching SLA *at creation time*.

Leakage controls
----------------
* Only information available when the ticket is created is used: priority,
  category, subcategory, channel, department, calendar features, the assigned
  agent's experience level, the agent's trailing 7-day workload and the
  customer's prior contact history. First response, reopen, escalation,
  resolution type and satisfaction are **excluded** (they happen later).
* Time-based split: train on tickets created in 2023-2024, test on 2025.
  The decision threshold is chosen on a 2024-H2 validation slice, never on test.
* Cross-validation uses ``TimeSeriesSplit`` so each fold trains on the past only.

The data is synthetic: these metrics demonstrate the method and say nothing
about real-world performance.
"""
from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.compose import ColumnTransformer  # noqa: E402
from sklearn.ensemble import HistGradientBoostingClassifier  # noqa: E402
from sklearn.inspection import permutation_importance  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import (average_precision_score, confusion_matrix, f1_score, precision_score,  # noqa: E402
                             recall_score, roc_auc_score, roc_curve)
from sklearn.model_selection import TimeSeriesSplit, cross_val_score  # noqa: E402
from sklearn.pipeline import Pipeline  # noqa: E402
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler  # noqa: E402

from src import config  # noqa: E402
from src.visualization.theme import INK, PRIMARY, SERIES, apply_matplotlib_theme  # noqa: E402

CAT = ["ticket_priority", "ticket_category", "ticket_subcategory", "support_channel", "department_id",
       "experience_level", "customer_segment", "created_dayname"]
NUM = ["created_hour", "created_month_num", "is_q4", "agent_load_7d", "customer_prior_tickets", "days_since_prev_ticket_f"]
LEAKY = ["first_response_hours", "reopened_count", "escalation_flag", "resolution_type", "satisfaction_score",
         "resolution_hours", "is_fcr"]


def build_features(t: pd.DataFrame) -> pd.DataFrame:
    """Creation-time features only (see module docstring)."""
    d = t[t.sla_eligible.astype(bool) & t.agent_id.notna()].copy()
    d = d.sort_values("ticket_created_date")
    d["created_month_num"] = d.ticket_created_date.dt.month
    d["is_q4"] = d.created_month_num.isin([11, 12]).astype(int)
    d["customer_prior_tickets"] = d.customer_ticket_seq - 1
    d["days_since_prev_ticket_f"] = d.days_since_prev_ticket.fillna(365).clip(upper=365)
    # trailing 7-day assignment count for the agent, using all tickets (incl. open
    # and cancelled) created strictly before this ticket
    allt = t[t.agent_id.notna()][["agent_id", "ticket_created_date"]].sort_values("ticket_created_date")
    allt["one"] = 1
    roll = (allt.set_index("ticket_created_date").groupby("agent_id").one
            .rolling("7D", closed="left").sum().reset_index().rename(columns={"one": "agent_load_7d"}))
    allt = allt.reset_index(drop=True)
    roll = roll.sort_values(["agent_id", "ticket_created_date"]).reset_index(drop=True)
    allt = allt.sort_values(["agent_id", "ticket_created_date"]).reset_index(drop=True)
    allt["agent_load_7d"] = roll.agent_load_7d.fillna(0).values
    load = allt.drop_duplicates(["agent_id", "ticket_created_date"], keep="first")
    d = d.merge(load[["agent_id", "ticket_created_date", "agent_load_7d"]], on=["agent_id", "ticket_created_date"], how="left")
    d["target"] = d.sla_breached.astype(int)
    assert not set(LEAKY) & set(CAT + NUM)
    return d


def _pipelines():
    lr = Pipeline([("prep", ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore", min_frequency=20), CAT),
                                               ("num", StandardScaler(), NUM)])),
                   ("clf", LogisticRegression(max_iter=2000, class_weight="balanced", C=0.5))])
    hgb = Pipeline([("prep", ColumnTransformer([("cat", OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1), CAT),
                                                ("num", "passthrough", NUM)])),
                    ("clf", HistGradientBoostingClassifier(learning_rate=0.06, max_iter=300, max_leaf_nodes=24,
                                                           l2_regularization=1.0, class_weight="balanced",
                                                           categorical_features=list(range(len(CAT))), random_state=config.SEED))])
    return {"Logistic Regression": lr, "Gradient Boosting": hgb}


def _best_threshold(y, p) -> float:
    grid = np.linspace(0.2, 0.8, 61)
    return float(grid[np.argmax([f1_score(y, p >= g) for g in grid])])


def train_and_evaluate(t: pd.DataFrame, out_dir=config.REPORTS_DATA_DIR, vis_dir=config.VIS_DIR) -> dict:
    apply_matplotlib_theme()
    d = build_features(t)
    train = d[d.ticket_created_date < "2025-01-01"]
    test = d[d.ticket_created_date >= "2025-01-01"]
    fit_part = train[train.ticket_created_date < "2024-07-01"]
    val_part = train[train.ticket_created_date >= "2024-07-01"]
    X = lambda df: df[CAT + NUM]  # noqa: E731
    results, probs = {}, {}
    for name, pipe in _pipelines().items():
        cv = cross_val_score(pipe, X(train), train.target, cv=TimeSeriesSplit(n_splits=5), scoring="roc_auc")
        pipe.fit(X(fit_part), fit_part.target)
        thr = _best_threshold(val_part.target, pipe.predict_proba(X(val_part))[:, 1])
        pipe.fit(X(train), train.target)                       # refit on all training data
        p = pipe.predict_proba(X(test))[:, 1]
        yhat = (p >= thr).astype(int)
        cm = confusion_matrix(test.target, yhat)
        results[name] = {
            "cv_roc_auc_mean": round(float(cv.mean()), 4), "cv_roc_auc_std": round(float(cv.std()), 4),
            "threshold": round(thr, 3),
            "test_roc_auc": round(float(roc_auc_score(test.target, p)), 4),
            "test_pr_auc": round(float(average_precision_score(test.target, p)), 4),
            "test_precision": round(float(precision_score(test.target, yhat)), 4),
            "test_recall": round(float(recall_score(test.target, yhat)), 4),
            "test_f1": round(float(f1_score(test.target, yhat)), 4),
            "confusion_matrix": {"tn": int(cm[0, 0]), "fp": int(cm[0, 1]), "fn": int(cm[1, 0]), "tp": int(cm[1, 1])},
        }
        probs[name] = (p, pipe)
    summary = {
        "target": "SLA breach (resolution_hours > sla_target_hours) for resolved tickets",
        "train_rows": len(train), "test_rows": len(test),
        "train_period": "2023-01-01 to 2024-12-31", "test_period": "2025-01-01 to 2025-12-31",
        "test_breach_rate_pct": round(test.target.mean() * 100, 2),
        "features_categorical": CAT, "features_numeric": NUM, "excluded_leaky_features": LEAKY,
        "models": results,
        "caveat": "Synthetic data. Metrics illustrate methodology only and are not evidence of real-world performance.",
    }
    best = max(results, key=lambda k: results[k]["test_roc_auc"])
    summary["selected_model"] = best

    # permutation importance for the selected model on the test set
    p_best, pipe_best = probs[best]
    imp = permutation_importance(pipe_best, X(test), test.target, scoring="roc_auc", n_repeats=5,
                                 random_state=config.SEED, n_jobs=1)
    fi = pd.DataFrame({"feature": CAT + NUM, "importance": imp.importances_mean, "std": imp.importances_std}) \
        .sort_values("importance", ascending=False)
    fi.to_csv(out_dir / "model_feature_importance.csv", index=False)
    summary["top_features"] = fi.head(6).round(4).to_dict("records")

    # risk deciles: breach rate by predicted-risk decile (calibration / usefulness view)
    dec = pd.qcut(p_best, 10, labels=False, duplicates="drop")
    deciles = test.assign(decile=dec + 1).groupby("decile").target.agg(["mean", "size"]).reset_index()
    deciles["breach_rate_pct"] = (deciles["mean"] * 100).round(2)
    deciles[["decile", "size", "breach_rate_pct"]].to_csv(out_dir / "model_risk_deciles.csv", index=False)
    summary["top_decile_breach_rate_pct"] = float(deciles.breach_rate_pct.iloc[-1])
    summary["bottom_decile_breach_rate_pct"] = float(deciles.breach_rate_pct.iloc[0])

    (out_dir / "model_metrics.json").write_text(json.dumps(summary, indent=2))

    # ---- charts
    fig, ax = plt.subplots(figsize=(6.5, 5))
    for i, (name, (p, _)) in enumerate(probs.items()):
        fpr, tpr, _ = roc_curve(test.target, p)
        ax.plot(fpr, tpr, color=SERIES[i], label=f"{name} (AUC {results[name]['test_roc_auc']:.3f})")
    ax.plot([0, 1], [0, 1], color=INK["muted"], ls="--", lw=1)
    ax.set_xlabel("False positive rate"); ax.set_ylabel("True positive rate")
    ax.set_title("SLA breach model - ROC curve (2025 hold-out)"); ax.legend(loc="lower right"); ax.grid(axis="x")
    fig.savefig(vis_dir / "48_model_roc_curve.png", dpi=150, bbox_inches="tight"); plt.close(fig)

    cm = results[best]["confusion_matrix"]
    m = np.array([[cm["tn"], cm["fp"]], [cm["fn"], cm["tp"]]])
    fig, ax = plt.subplots(figsize=(5.2, 4.4))
    ax.imshow(m, cmap=matplotlib.colors.LinearSegmentedColormap.from_list("b", ["#eef4fc", PRIMARY]))
    for (i, j), v in np.ndenumerate(m):
        ax.text(j, i, f"{v:,}", ha="center", va="center", fontsize=13, color="white" if v > m.max() / 2 else INK["primary"])
    ax.set_xticks([0, 1], ["Predicted: within SLA", "Predicted: breach"]); ax.set_yticks([0, 1], ["Actual: within", "Actual: breach"])
    ax.grid(False); ax.set_title(f"Confusion matrix - {best}\n(threshold {results[best]['threshold']})")
    fig.savefig(vis_dir / "49_model_confusion_matrix.png", dpi=150, bbox_inches="tight"); plt.close(fig)

    f = fi.head(10).iloc[::-1]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.barh(f.feature, f.importance, xerr=f["std"], color=PRIMARY, height=0.6, error_kw=dict(ecolor=INK["muted"], lw=1))
    ax.set_xlabel("Drop in ROC-AUC when feature is shuffled"); ax.grid(axis="x"); ax.grid(axis="y", visible=False)
    ax.set_title(f"Permutation feature importance - {best}")
    fig.savefig(vis_dir / "50_model_feature_importance.png", dpi=150, bbox_inches="tight"); plt.close(fig)
    return summary


def main() -> None:
    from src.data_cleaning.loader import load_processed
    s = train_and_evaluate(load_processed("tickets_enriched"))
    print(json.dumps({k: s[k] for k in ("selected_model", "models", "top_decile_breach_rate_pct",
                                        "bottom_decile_breach_rate_pct")}, indent=2))


if __name__ == "__main__":
    main()

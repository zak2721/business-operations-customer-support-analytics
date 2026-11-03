"""End-to-end cleaning pipeline: raw -> validated, cleaned, feature-rich data.

Run:
    python -m src.data_cleaning.pipeline
"""
from __future__ import annotations

import json
import logging
from datetime import datetime

import numpy as np
import pandas as pd

from src import config
from src.data_cleaning import cleaners as c
from src.data_cleaning.loader import load_all_raw
from src.data_validation import validators as v
from src.feature_engineering import features as fe

log = logging.getLogger(__name__)

PRIMARY_KEYS = {
    "customers": "customer_id", "departments": "department_id", "agents": "agent_id",
    "support_tickets": "ticket_id", "customer_feedback": "feedback_id", "operations": "operation_id",
    "agent_performance": "performance_id", "business_costs": "cost_id", "calendar": "date",
}
CRITICAL_COLUMNS = {
    "customers": ["customer_id", "customer_name", "customer_segment", "customer_region", "customer_country",
                  "customer_type", "registration_date", "customer_status", "customer_lifetime_value"],
    "departments": ["department_id", "department_name", "department_manager", "operational_budget"],
    "agents": ["agent_id", "agent_name", "team", "department_id", "hire_date", "experience_level"],
    "support_tickets": ["ticket_id", "customer_id", "agent_id", "department_id", "ticket_created_date",
                        "ticket_category", "ticket_priority", "ticket_status", "support_channel", "sla_target_hours"],
    "customer_feedback": ["feedback_id", "ticket_id", "customer_id", "feedback_date", "satisfaction_score",
                          "customer_rating", "feedback_category"],
    "operations": ["operation_id", "department_id", "operation_date", "total_transactions", "successful_transactions",
                   "failed_transactions", "processing_time_minutes", "operational_cost"],
    "agent_performance": ["performance_id", "agent_id", "performance_date", "tickets_assigned", "tickets_resolved",
                          "workload_hours"],
    "business_costs": ["cost_id", "department_id", "cost_date", "direct_cost", "indirect_cost", "total_cost"],
    "calendar": ["date", "year", "month"],
}
# Issue types that make a row "invalid" (as opposed to merely missing/duplicate)
INVALID_TYPES = {"Inconsistent label", "Inconsistent value", "Impossible timestamp", "Out of range",
                 "Orphan key", "Invalid value", "Outlier", "Data type / format"}


def run_cleaning(raw: dict[str, pd.DataFrame] | None = None) -> tuple[dict[str, pd.DataFrame], c.IssueLog]:
    """Clean every table in dependency order. Returns (clean tables, issue log)."""
    raw = raw if raw is not None else load_all_raw()
    raw = {k: df.copy() for k, df in raw.items()}  # never mutate the inputs
    il = c.IssueLog()
    out: dict[str, pd.DataFrame] = {}
    out["departments"] = c.clean_departments(raw["departments"], il)
    out["agents"] = c.clean_agents(raw["agents"], out["departments"], il)
    out["customers"] = c.clean_customers(raw["customers"], il)
    out["support_tickets"] = c.clean_tickets(raw["support_tickets"], out["customers"], out["agents"],
                                             out["departments"], il)
    out["customer_feedback"] = c.clean_feedback(raw["customer_feedback"], out["support_tickets"], il)
    out["operations"] = c.clean_operations(raw["operations"], out["departments"], il)
    out["business_costs"] = c.clean_costs(raw["business_costs"], il)
    out["agent_performance"] = c.clean_performance(raw["agent_performance"], out["agents"], il)
    out["calendar"] = c.clean_calendar(raw["calendar"], il)
    return out, il


def add_features(clean: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    clean = dict(clean)
    clean["support_tickets"] = fe.ticket_features(clean["support_tickets"])
    clean["operations"] = fe.operations_features(clean["operations"])
    clean["tickets_enriched"] = fe.enrich_tickets(clean["support_tickets"], clean["customers"], clean["agents"],
                                                  clean["departments"], clean["customer_feedback"])
    return clean


def quality_scores(raw: dict[str, pd.DataFrame], clean: dict[str, pd.DataFrame], il: c.IssueLog) -> pd.DataFrame:
    """Before/after quality score per table (completeness 40%, uniqueness 30%, validity 30%)."""
    logdf = il.to_frame()
    rows = []
    for name in config.ACTIVE_RAW_FILES:
        r, p = raw[name], clean[name]
        key = PRIMARY_KEYS[name]
        affected = logdf[(logdf.table == name) & logdf.issue_type.isin(INVALID_TYPES)].records_affected.sum()
        invalid_before = pd.Series(np.arange(len(r)) < min(affected, len(r)))
        p_eval = p.copy()
        if name == "support_tickets":
            p_eval["support_channel"] = p_eval.support_channel.replace("Unknown", np.nan)
        before = v.quality_dimensions(r, CRITICAL_COLUMNS[name], key, invalid_before)
        after = v.quality_dimensions(p_eval, CRITICAL_COLUMNS[name], key, None)
        t_log = logdf[logdf.table == name]
        rows.append({
            "table": name, "raw_records": len(r), "clean_records": len(p),
            "records_removed": len(r) - len(p),
            "records_corrected": int(t_log[t_log.action == "corrected"].records_affected.sum()),
            "records_imputed": int(t_log[t_log.action == "imputed"].records_affected.sum()),
            "records_flagged": int(t_log[t_log.action == "flagged"].records_affected.sum()),
            "missing_cells_raw": int(r.isna().sum().sum()),
            "duplicate_rows_raw": v.exact_duplicates(r),
            **{f"{k}_before": val for k, val in before.items()},
            **{f"{k}_after": val for k, val in after.items()},
        })
    return pd.DataFrame(rows)


def write_quality_report(raw, clean, il: c.IssueLog, scores: pd.DataFrame, out_dir=config.REPORTS_DATA_DIR) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    logdf = il.to_frame()
    logdf.to_csv(out_dir / "data_quality_issue_log.csv", index=False)
    scores.to_csv(out_dir / "data_quality_scores.csv", index=False)
    pd.concat([v.profile(raw[n], n) for n in config.ACTIVE_RAW_FILES]).to_csv(out_dir / "column_profile_raw.csv", index=False)
    pd.concat([v.profile(clean[n], n) for n in config.ACTIVE_RAW_FILES]).to_csv(out_dir / "column_profile_processed.csv", index=False)

    tot_raw, tot_clean = scores.raw_records.sum(), scores.clean_records.sum()
    w = scores.raw_records / tot_raw
    overall_before = float((scores.quality_score_before * w).sum())
    overall_after = float((scores.quality_score_after * w).sum())
    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "total_raw_records": int(tot_raw), "total_clean_records": int(tot_clean),
        "records_removed": int(scores.records_removed.sum()),
        "records_corrected": int(scores.records_corrected.sum()),
        "records_imputed": int(scores.records_imputed.sum()),
        "records_flagged": int(scores.records_flagged.sum()),
        "missing_cells_raw": int(scores.missing_cells_raw.sum()),
        "duplicate_rows_raw": int(scores.duplicate_rows_raw.sum()),
        "quality_score_before": round(overall_before, 2), "quality_score_after": round(overall_after, 2),
    }
    (out_dir / "data_quality_summary.json").write_text(json.dumps(summary, indent=2))

    def md_table(df: pd.DataFrame) -> str:
        cols = list(df.columns)
        lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
        lines += ["| " + " | ".join(str(x) for x in row) + " |" for row in df.itertuples(index=False)]
        return "\n".join(lines)

    md = [
        "# Data Quality Report", "",
        f"_Generated by `src/data_cleaning/pipeline.py` on {summary['generated_at']}. All figures below are computed, not typed._", "",
        "## Summary", "",
        f"* Raw records across 9 tables: **{tot_raw:,}** → clean records: **{tot_clean:,}**",
        f"* Records removed: **{summary['records_removed']:,}** (exact duplicates and unlinkable orphan feedback only)",
        f"* Records corrected (value derivable from other fields): **{summary['records_corrected']:,}**",
        f"* Records imputed (estimated + flag column): **{summary['records_imputed']:,}**",
        f"* Records flagged (kept, problem value nulled or marked): **{summary['records_flagged']:,}**",
        f"* Missing cells in raw data: **{summary['missing_cells_raw']:,}** (includes legitimate NULLs such as resolved_date on open tickets)",
        f"* Overall data quality score: **{overall_before:.1f} → {overall_after:.1f}** (record-weighted)", "",
        "### Scoring method", "",
        "`quality_score = 0.4 × completeness + 0.3 × uniqueness + 0.3 × validity`, computed per table on its critical columns. "
        "Completeness after cleaning treats the 'Unknown' channel placeholder as missing so the score is not inflated.", "",
        "## Scores by table", "",
        md_table(scores[["table", "raw_records", "clean_records", "records_removed", "records_corrected",
                         "records_imputed", "records_flagged", "quality_score_before", "quality_score_after"]]), "",
        "## Issue log and cleaning decisions", "",
        md_table(logdf[logdf.records_affected > 0]), "",
        "## Checks that passed with zero issues", "",
        md_table(logdf[logdf.records_affected == 0][["table", "check", "decision"]]), "",
        "## Principles", "",
        "1. Raw files in `data/raw/` are never modified.",
        "2. Rows are removed only when they are exact duplicates or cannot be linked to any parent record.",
        "3. Imputed values always carry a boolean flag column (`clv_imputed`, `processing_time_imputed`, `cost_outlier`, ...).",
        "4. Satisfaction scores are never imputed - imputing survey answers would bias CSAT.",
        "5. Tickets with impossible timestamps are kept for volume KPIs but excluded from time-based KPIs.",
    ]
    (out_dir / "data_quality_report.md").write_text("\n".join(md))


def export_processed(tables: dict[str, pd.DataFrame], out_dir=config.PROCESSED_DIR) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        df.to_csv(out_dir / f"{name}.csv", index=False, date_format="%Y-%m-%d %H:%M:%S")


def main() -> dict[str, pd.DataFrame]:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    raw = load_all_raw()
    clean, il = run_cleaning(raw)
    scores = quality_scores(raw, clean, il)
    tables = add_features(clean)
    export_processed(tables)
    write_quality_report(raw, clean, il, scores)
    log.info("Quality score before/after:\n%s", scores[["table", "quality_score_before", "quality_score_after"]])
    return tables


if __name__ == "__main__":
    main()

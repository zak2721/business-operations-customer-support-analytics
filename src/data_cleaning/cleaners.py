"""Table-specific cleaning rules.

Every rule records what it found and what it did in an ``IssueLog`` so that
no record is changed or removed silently. Actions use a fixed vocabulary:

* ``removed``   - row dropped (only exact duplicates and unlinkable orphans)
* ``corrected`` - value replaced by a value derivable from other fields
* ``imputed``   - value estimated (always accompanied by a boolean flag column)
* ``flagged``   - value kept or nulled, row kept, flag column added
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from src import config
from src.data_generation.reference_data import REGIONS
from src.data_validation import validators as v

CHANNEL_MAP = {
    "email": "Email", "e-mail": "Email",
    "phone": "Phone",
    "live chat": "Live Chat", "chat": "Live Chat", "livechat": "Live Chat",
    "web portal": "Web Portal", "web": "Web Portal",
    "social media": "Social Media", "social": "Social Media",
}
SEGMENT_MAP = {"enterprise": "Enterprise", "mid-market": "Mid-Market",
               "small business": "Small Business", "consumer": "Consumer"}
COUNTRY_TO_REGION = {c: r for r, (_, countries, _) in REGIONS.items() for c in countries}


@dataclass
class IssueLog:
    """Collects one entry per cleaning rule applied."""
    entries: list[dict] = field(default_factory=list)

    def add(self, table: str, check: str, issue_type: str, records: int, action: str, decision: str) -> None:
        self.entries.append({"table": table, "check": check, "issue_type": issue_type,
                             "records_affected": int(records), "action": action, "decision": decision})

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.entries, columns=["table", "check", "issue_type", "records_affected", "action", "decision"])


def parse_mixed_dates(s: pd.Series) -> pd.Series:
    """Parse ISO dates first, then fall back to the 'DD-Mon-YYYY' legacy format."""
    iso = pd.to_datetime(s, format="%Y-%m-%d", errors="coerce")
    alt = pd.to_datetime(s, format="%d-%b-%Y", errors="coerce")
    return iso.fillna(alt)


def drop_exact_duplicates(df: pd.DataFrame, table: str, log: IssueLog) -> pd.DataFrame:
    n = v.exact_duplicates(df)
    if n:
        log.add(table, "exact_duplicates", "Duplicate", n, "removed",
                "Rows identical in every column are copies of the same event; the first occurrence is kept.")
    return df.drop_duplicates().reset_index(drop=True)


# --------------------------------------------------------------------------
def clean_departments(df: pd.DataFrame, log: IssueLog) -> pd.DataFrame:
    df = drop_exact_duplicates(df, "departments", log)
    assert v.is_primary_key(df, "department_id"), "department_id is not a valid primary key"
    neg = (df.operational_budget < 0).sum()
    if neg:
        log.add("departments", "negative_budget", "Invalid value", neg, "flagged", "Budgets must be non-negative.")
    return df


def clean_agents(df: pd.DataFrame, departments: pd.DataFrame, log: IssueLog) -> pd.DataFrame:
    df = drop_exact_duplicates(df, "agents", log)
    df["hire_date"] = pd.to_datetime(df.hire_date, errors="coerce")
    orphan = v.orphan_keys(df, "department_id", departments, "department_id").sum()
    if orphan:
        log.add("agents", "fk_department", "Orphan key", orphan, "flagged", "Agent references unknown department.")
    assert v.is_primary_key(df, "agent_id")
    return df


def clean_customers(df: pd.DataFrame, log: IssueLog) -> pd.DataFrame:
    t = "customers"
    df = drop_exact_duplicates(df, t, log)
    kd = v.key_duplicates(df, "customer_id")
    if kd:  # conflicting duplicates: keep the most complete row
        df = df.assign(_nn=df.notna().sum(axis=1)).sort_values(["customer_id", "_nn"], ascending=[True, False])
        df = df.drop_duplicates("customer_id").drop(columns="_nn")
        log.add(t, "conflicting_key_duplicates", "Duplicate", kd, "removed",
                "Same customer_id with different values: kept the most complete record.")

    seg_bad = ~df.customer_segment.isin(SEGMENT_MAP.values())
    df["customer_segment"] = df.customer_segment.str.strip().str.lower().map(SEGMENT_MAP)
    log.add(t, "segment_label_case", "Inconsistent label", seg_bad.sum(), "corrected",
            "Segment labels standardised to the four canonical values (case-insensitive match).")

    raw_dates = df.registration_date.astype(str)
    alt_fmt = ~raw_dates.str.match(r"^\d{4}-\d{2}-\d{2}$")
    df["registration_date"] = parse_mixed_dates(raw_dates)
    log.add(t, "registration_date_format", "Data type / format", alt_fmt.sum(), "corrected",
            "Legacy 'DD-Mon-YYYY' dates converted to ISO dates; unparseable values would become NaT.")
    if df.registration_date.isna().any():
        log.add(t, "registration_date_unparseable", "Invalid value", df.registration_date.isna().sum(), "flagged",
                "Registration date could not be parsed.")

    miss_region = df.customer_region.isna()
    df.loc[miss_region, "customer_region"] = df.loc[miss_region, "customer_country"].map(COUNTRY_TO_REGION)
    log.add(t, "missing_region", "Missing value", miss_region.sum(), "corrected",
            "Region is fully determined by country, so missing regions are derived from customer_country.")

    miss_clv = df.customer_lifetime_value.isna()
    df["clv_imputed"] = miss_clv
    seg_median = df.groupby("customer_segment").customer_lifetime_value.transform("median")
    df["customer_lifetime_value"] = df.customer_lifetime_value.fillna(seg_median).round(2)
    log.add(t, "missing_clv", "Missing value", miss_clv.sum(), "imputed",
            "CLV imputed with the segment median (CLV differs ~20x across segments); rows flagged clv_imputed.")
    neg = (df.customer_lifetime_value < 0).sum()
    log.add(t, "negative_clv", "Invalid value", neg, "flagged", "CLV must be non-negative.") if neg else None
    return df.sort_values("customer_id").reset_index(drop=True)


def clean_tickets(df: pd.DataFrame, customers: pd.DataFrame, agents: pd.DataFrame,
                  departments: pd.DataFrame, log: IssueLog) -> pd.DataFrame:
    t = "support_tickets"
    df = drop_exact_duplicates(df, t, log)
    assert v.is_primary_key(df, "ticket_id"), "ticket_id still duplicated after removing exact duplicates"

    for col in ("ticket_created_date", "first_response_date", "resolved_date"):
        df[col] = pd.to_datetime(df[col], errors="coerce")

    # --- categorical standardisation
    raw_ch = df.support_channel
    df["support_channel"] = raw_ch.str.strip().str.lower().map(CHANNEL_MAP)
    variants = raw_ch.notna() & (raw_ch != df.support_channel)
    log.add(t, "channel_label_variants", "Inconsistent label", variants.sum(), "corrected",
            "Channel spellings (e.g. 'E-mail', 'chat') mapped to 5 canonical channels.")
    miss_ch = df.support_channel.isna()
    df.loc[miss_ch, "support_channel"] = "Unknown"
    log.add(t, "missing_channel", "Missing value", miss_ch.sum(), "imputed",
            "Channel cannot be inferred from other fields; labelled 'Unknown' so tickets still count in totals.")

    bad_case = ~df.ticket_priority.isin(config.SLA_TARGET_HOURS)
    df["ticket_priority"] = df.ticket_priority.str.strip().str.title()
    log.add(t, "priority_label_case", "Inconsistent label", bad_case.sum(), "corrected",
            "Priority labels standardised to Title Case.")

    bad_status = ~df.ticket_status.isin(config.TICKET_STATUSES)
    if bad_status.any():
        log.add(t, "invalid_status", "Invalid value", bad_status.sum(), "flagged", "Status outside the allowed list.")

    expected_sla = df.ticket_priority.map(config.SLA_TARGET_HOURS)
    wrong_sla = df.sla_target_hours != expected_sla
    df["sla_target_hours"] = expected_sla.astype(int)
    log.add(t, "sla_target_vs_priority", "Inconsistent value", wrong_sla.sum(), "corrected",
            "SLA target is a business rule of priority (Critical 8h, High 24h, Medium 48h, Low 72h); recomputed.")

    # --- referential integrity
    orphan_agent = v.orphan_keys(df, "agent_id", agents, "agent_id")
    df["agent_unknown"] = orphan_agent
    df.loc[orphan_agent, "agent_id"] = np.nan
    log.add(t, "fk_agent", "Orphan key", orphan_agent.sum(), "flagged",
            "agent_id not in agent master: set to NULL (kept for volume KPIs, excluded from agent-level KPIs).")
    for fk, parent, pk in (("customer_id", customers, "customer_id"), ("department_id", departments, "department_id")):
        n = v.orphan_keys(df, fk, parent, pk).sum()
        log.add(t, f"fk_{pk.split('_')[0]}", "Orphan key", n, "flagged" if n else "none",
                f"{fk} validated against master table.")

    # --- chronology
    bad_res = v.chronology_violations(df, "ticket_created_date", "resolved_date")
    df["resolution_ts_invalid"] = bad_res
    df.loc[bad_res, "resolved_date"] = pd.NaT
    log.add(t, "resolved_before_created", "Impossible timestamp", bad_res.sum(), "flagged",
            "Resolution timestamp precedes creation (impossible). Timestamp nulled; ticket kept as resolved for "
            "counts but excluded from resolution-time and SLA calculations.")
    bad_frt = v.chronology_violations(df, "ticket_created_date", "first_response_date")
    df.loc[bad_frt, "first_response_date"] = pd.NaT
    log.add(t, "response_before_created", "Impossible timestamp", bad_frt.sum(), "flagged" if bad_frt.any() else "none",
            "First response before creation is impossible; timestamp nulled.")
    resp_after_res = v.chronology_violations(df, "first_response_date", "resolved_date")
    log.add(t, "response_after_resolution", "Impossible timestamp", resp_after_res.sum(),
            "flagged" if resp_after_res.any() else "none", "First response must not be after resolution.")

    resolved_status = df.ticket_status.isin(config.RESOLVED_STATUSES)
    miss_frt = resolved_status & df.first_response_date.isna()
    df["first_response_missing"] = miss_frt
    log.add(t, "resolved_missing_first_response", "Missing value", miss_frt.sum(), "flagged",
            "Resolved tickets without a first-response timestamp are kept; excluded from FRT averages only.")
    open_with_res = df.ticket_status.isin(config.UNRESOLVED_STATUSES | config.EXCLUDED_STATUSES) & df.resolved_date.notna()
    df.loc[open_with_res, "resolved_date"] = pd.NaT
    log.add(t, "unresolved_with_resolved_date", "Inconsistent value", open_with_res.sum(),
            "corrected" if open_with_res.any() else "none",
            "Open/pending/cancelled tickets must not carry a resolution date.")

    reg = df.customer_id.map(customers.set_index("customer_id").registration_date)
    before_reg = df.ticket_created_date < reg
    log.add(t, "ticket_before_registration", "Impossible timestamp", before_reg.sum(),
            "flagged" if before_reg.any() else "none", "Ticket cannot pre-date customer registration.")

    agent_dept = df.agent_id.map(agents.set_index("agent_id").department_id)
    dept_mismatch = agent_dept.notna() & (agent_dept != df.department_id)
    log.add(t, "agent_department_consistency", "Inconsistent value", dept_mismatch.sum(),
            "flagged" if dept_mismatch.any() else "none", "Ticket department should match assigned agent's department.")

    frt_h = (df.first_response_date - df.ticket_created_date).dt.total_seconds() / 3600
    extreme = frt_h > 24 * 14
    log.add(t, "extreme_first_response", "Outlier", extreme.sum(), "flagged" if extreme.any() else "none",
            "First response > 14 days is implausible; retained but reviewable.")
    df["reopened_count"] = df.reopened_count.astype(int)
    df["escalation_flag"] = df.escalation_flag.astype(int)
    return df.sort_values("ticket_id").reset_index(drop=True)


def clean_feedback(df: pd.DataFrame, tickets: pd.DataFrame, log: IssueLog) -> pd.DataFrame:
    t = "customer_feedback"
    df = drop_exact_duplicates(df, t, log)
    df["feedback_date"] = pd.to_datetime(df.feedback_date, errors="coerce")
    orphan = ~df.ticket_id.isin(tickets.ticket_id)
    log.add(t, "fk_ticket", "Orphan key", orphan.sum(), "removed",
            "Feedback that references a non-existent ticket cannot be attributed to any agent, channel or "
            "category; removed (count reported).")
    df = df[~orphan].copy()

    multi = df.ticket_id.duplicated(keep="last")
    if multi.any():
        log.add(t, "multiple_feedback_per_ticket", "Duplicate", multi.sum(), "removed",
                "Only the latest survey response per ticket is kept, so CSAT is not double counted.")
        df = df.sort_values("feedback_date").drop_duplicates("ticket_id", keep="last")

    true_cust = df.ticket_id.map(tickets.set_index("ticket_id").customer_id)
    mismatch = df.customer_id != true_cust
    df["customer_id"] = true_cust
    log.add(t, "customer_matches_ticket", "Inconsistent value", mismatch.sum(), "corrected",
            "customer_id on feedback must equal the ticket's customer; replaced with the ticket's customer_id.")

    lo, hi = config.SATISFACTION_SCALE
    score = pd.to_numeric(df.satisfaction_score, errors="coerce")
    bad = v.out_of_range(score, lo, hi)
    df["satisfaction_score_invalid"] = bad
    df["satisfaction_score"] = score.where(~bad)
    log.add(t, "satisfaction_scale", "Out of range", bad.sum(), "flagged",
            f"Scores outside {lo}-{hi} cannot be mapped reliably; set to NULL and flagged (record kept for rating).")
    log.add(t, "missing_satisfaction", "Missing value", score.isna().sum(), "flagged",
            "Missing CSAT is not imputed: averaging imputed scores would bias satisfaction KPIs.")
    rlo, rhi = config.RATING_SCALE
    rbad = v.out_of_range(df.customer_rating, rlo, rhi)
    df.loc[rbad, "customer_rating"] = np.nan
    log.add(t, "rating_scale", "Out of range", rbad.sum(), "flagged" if rbad.any() else "none", "Rating must be 1-10.")

    res = df.ticket_id.map(tickets.set_index("ticket_id").resolved_date)
    early = res.notna() & (df.feedback_date < res)
    log.add(t, "feedback_before_resolution", "Impossible timestamp", early.sum(),
            "flagged" if early.any() else "none", "Survey should be sent after resolution.")
    df["satisfaction_score"] = df.satisfaction_score.astype(float)
    return df.sort_values("feedback_id").reset_index(drop=True)


def clean_operations(df: pd.DataFrame, departments: pd.DataFrame, log: IssueLog) -> pd.DataFrame:
    t = "operations"
    df = drop_exact_duplicates(df, t, log)
    df["operation_date"] = pd.to_datetime(df.operation_date, errors="coerce")
    df["month"] = df.operation_date.dt.to_period("M").astype(str)

    mismatch = df.successful_transactions + df.failed_transactions != df.total_transactions
    df.loc[mismatch, "successful_transactions"] = df.loc[mismatch, "total_transactions"] - df.loc[mismatch, "failed_transactions"]
    log.add(t, "success_plus_failed_equals_total", "Inconsistent value", mismatch.sum(), "corrected",
            "successful + failed must equal total; total and failed come from the system log, so successful is recomputed.")

    neg = df.operational_cost < 0
    df["cost_sign_corrected"] = neg
    df.loc[neg, "operational_cost"] = df.loc[neg, "operational_cost"].abs()
    log.add(t, "negative_cost", "Invalid value", neg.sum(), "corrected",
            "Costs cannot be negative. Magnitudes match the process's normal range, indicating a sign-entry error; "
            "absolute value used and row flagged.")

    cpt = df.operational_cost / df.total_transactions.replace(0, np.nan)
    z = cpt.groupby([df.process_name]).transform(lambda s: v.robust_zscore(s))
    outlier = z.abs() > 8
    df["cost_outlier"] = outlier
    df["operational_cost_original"] = df.operational_cost
    expected_cpt = cpt.where(~outlier).groupby([df.process_name, df.month]).transform("median")
    df.loc[outlier, "operational_cost"] = (expected_cpt[outlier] * df.loc[outlier, "total_transactions"]).round(2)
    log.add(t, "cost_outlier_robust_z", "Outlier", outlier.sum(), "imputed",
            "Cost-per-transaction robust z-score > 8 within process (10x+ normal). Treated as entry errors: cost "
            "replaced with process-month median cost/txn x volume; original kept in operational_cost_original.")

    miss_pt = df.processing_time_minutes.isna()
    df["processing_time_imputed"] = miss_pt
    med = df.groupby(["process_name", "month"]).processing_time_minutes.transform("median")
    df["processing_time_minutes"] = df.processing_time_minutes.fillna(med)
    log.add(t, "missing_processing_time", "Missing value", miss_pt.sum(), "imputed",
            "Imputed with the same process's median for that month; flagged processing_time_imputed.")

    orphan = v.orphan_keys(df, "department_id", departments, "department_id").sum()
    log.add(t, "fk_department", "Orphan key", orphan, "flagged" if orphan else "none", "Department validated.")
    return df.drop(columns="month")


def clean_costs(df: pd.DataFrame, log: IssueLog) -> pd.DataFrame:
    t = "business_costs"
    df = drop_exact_duplicates(df, t, log)
    df["cost_date"] = pd.to_datetime(df.cost_date, errors="coerce")
    miss_ind = df.indirect_cost.isna() & df.total_cost.notna()
    df.loc[miss_ind, "indirect_cost"] = (df.loc[miss_ind, "total_cost"] - df.loc[miss_ind, "direct_cost"]).round(2)
    log.add(t, "missing_indirect_cost", "Missing value", miss_ind.sum(), "corrected",
            "indirect = total - direct (exact derivation, not an estimate).")
    calc = (df.direct_cost + df.indirect_cost).round(2)
    mismatch = (calc - df.total_cost).abs() > 0.02
    df.loc[mismatch, "total_cost"] = calc[mismatch]
    log.add(t, "total_equals_components", "Inconsistent value", mismatch.sum(), "corrected",
            "total_cost recomputed as direct + indirect (components are the source of truth).")
    neg = (df[["direct_cost", "indirect_cost", "total_cost"]] < 0).any(axis=1).sum()
    log.add(t, "negative_cost", "Invalid value", neg, "flagged" if neg else "none", "Costs must be non-negative.")
    return df


def clean_performance(df: pd.DataFrame, agents: pd.DataFrame, log: IssueLog) -> pd.DataFrame:
    t = "agent_performance"
    df = drop_exact_duplicates(df, t, log)
    df["performance_date"] = pd.to_datetime(df.performance_date, errors="coerce")
    bad = v.out_of_range(df.sla_compliance_rate, 0, 100)
    df.loc[bad, "sla_compliance_rate"] = np.nan
    log.add(t, "sla_rate_0_100", "Out of range", bad.sum(), "flagged",
            "A percentage cannot exceed 100; set to NULL (recomputable from ticket data).")
    bad_csat = v.out_of_range(df.customer_satisfaction_score, *config.SATISFACTION_SCALE)
    log.add(t, "csat_scale", "Out of range", bad_csat.sum(), "flagged" if bad_csat.any() else "none", "Monthly agent CSAT averages must lie on the 1-5 survey scale.")
    over = df.tickets_resolved > df.tickets_assigned * 3 + 10
    log.add(t, "resolved_vs_assigned", "Plausibility", over.sum(), "flagged" if over.any() else "none",
            "Resolved counts by resolution month can legitimately exceed same-month assignments; only extreme gaps flagged.")
    orphan = v.orphan_keys(df, "agent_id", agents, "agent_id").sum()
    log.add(t, "fk_agent", "Orphan key", orphan, "flagged" if orphan else "none", "Agent validated.")
    return df


def clean_calendar(df: pd.DataFrame, log: IssueLog) -> pd.DataFrame:
    df["date"] = pd.to_datetime(df.date)
    gaps = (df.date.diff().dt.days.dropna() != 1).sum()
    log.add("calendar", "contiguous_dates", "Completeness", gaps, "flagged" if gaps else "none",
            "Date dimension must have one row per day with no gaps.")
    return df

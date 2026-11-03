"""Analytical features derived from cleaned tables.

The ticket-level flags created here (``is_resolved``, ``sla_eligible``,
``sla_met``, ``is_fcr`` ...) are the single source of truth for KPI
denominators used by the Python KPI engine, SQL views and Power BI measures.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src import config

AGING_BINS = [-1, 2, 7, 14, 30, 60, 10_000]
AGING_LABELS = ["0-2 days", "3-7 days", "8-14 days", "15-30 days", "31-60 days", "60+ days"]
RES_BINS = [-0.001, 1, 4, 24, 48, 72, 168, 100_000]
RES_LABELS = ["<1h", "1-4h", "4-24h", "1-2 days", "2-3 days", "3-7 days", "7+ days"]
REPEAT_WINDOW_DAYS = 7


def ticket_features(t: pd.DataFrame, snapshot: str = config.SNAPSHOT_DATE) -> pd.DataFrame:
    """Add time, status, SLA, FCR, aging and repeat-contact features."""
    t = t.copy()
    snap = pd.Timestamp(snapshot)
    t["first_response_hours"] = ((t.first_response_date - t.ticket_created_date).dt.total_seconds() / 3600).round(3)
    t["resolution_hours"] = ((t.resolved_date - t.ticket_created_date).dt.total_seconds() / 3600).round(3)

    t["is_cancelled"] = t.ticket_status.isin(config.EXCLUDED_STATUSES)
    t["is_resolved"] = t.ticket_status.isin(config.RESOLVED_STATUSES)
    t["is_unresolved"] = t.ticket_status.isin(config.UNRESOLVED_STATUSES)
    # SLA eligibility: resolved with a valid resolution timestamp (cancelled and
    # open tickets are excluded; open tickets are tracked by aging/exposure).
    t["sla_eligible"] = t.is_resolved & t.resolved_date.notna()
    t["sla_met"] = np.where(t.sla_eligible, t.resolution_hours <= t.sla_target_hours, np.nan)
    t["sla_breached"] = np.where(t.sla_eligible, t.resolution_hours > t.sla_target_hours, np.nan)
    t["frt_target_hours"] = t.ticket_priority.map(config.FRT_TARGET_HOURS)
    t["frt_met"] = np.where(t.first_response_hours.notna(), t.first_response_hours <= t.frt_target_hours, np.nan)
    t["is_reopened"] = t.reopened_count > 0
    t["is_escalated"] = t.escalation_flag == 1
    # First-contact resolution: resolved in the first interaction, never
    # reopened and never escalated.
    t["is_fcr"] = (t.sla_eligible & (t.resolution_type == "First Contact Resolution")
                   & ~t.is_reopened & ~t.is_escalated)

    t["created_date"] = t.ticket_created_date.dt.normalize()
    t["created_year"] = t.ticket_created_date.dt.year
    t["created_month"] = t.ticket_created_date.dt.to_period("M").astype(str)
    t["created_quarter"] = t.ticket_created_date.dt.to_period("Q").astype(str)
    t["created_hour"] = t.ticket_created_date.dt.hour
    t["created_dayname"] = t.ticket_created_date.dt.day_name()
    t["created_weekday"] = t.ticket_created_date.dt.dayofweek < 5
    t["resolved_month"] = t.resolved_date.dt.to_period("M").astype(str).replace("NaT", np.nan)

    t["ticket_age_days"] = np.where(t.is_unresolved, (snap - t.ticket_created_date).dt.total_seconds() / 86400, np.nan)
    t["ticket_age_days"] = t.ticket_age_days.round(2)
    t["aging_bucket"] = pd.cut(t.ticket_age_days, AGING_BINS, labels=AGING_LABELS).astype(object)
    t["aging_sla_exposed"] = t.is_unresolved & (t.ticket_age_days * 24 > t.sla_target_hours)
    t["resolution_bucket"] = pd.cut(t.resolution_hours, RES_BINS, labels=RES_LABELS).astype(object)

    t = t.sort_values(["customer_id", "ticket_created_date"])
    prev = t.groupby("customer_id").ticket_created_date.shift()
    t["days_since_prev_ticket"] = ((t.ticket_created_date - prev).dt.total_seconds() / 86400).round(2)
    t["customer_ticket_seq"] = t.groupby("customer_id").cumcount() + 1
    t["is_repeat_contact"] = t.days_since_prev_ticket.le(REPEAT_WINDOW_DAYS).fillna(False)
    return t.sort_values("ticket_id").reset_index(drop=True)


def operations_features(o: pd.DataFrame) -> pd.DataFrame:
    o = o.copy()
    tot = o.total_transactions.replace(0, np.nan)
    o["success_rate"] = (o.successful_transactions / tot * 100).round(3)
    o["failure_rate"] = (o.failed_transactions / tot * 100).round(3)
    o["cost_per_transaction"] = (o.operational_cost / tot).round(4)
    o["total_processing_hours"] = (o.processing_time_minutes * o.total_transactions / 60).round(2)
    o["operation_month"] = o.operation_date.dt.to_period("M").astype(str)
    return o


def enrich_tickets(t: pd.DataFrame, customers: pd.DataFrame, agents: pd.DataFrame,
                   departments: pd.DataFrame, feedback: pd.DataFrame) -> pd.DataFrame:
    """One row per ticket with descriptive attributes and its (single) survey.

    Feedback is deduplicated to one row per ticket upstream, so this left join
    cannot multiply ticket rows (asserted).
    """
    n = len(t)
    out = (t.merge(customers[["customer_id", "customer_segment", "customer_region", "customer_country", "customer_type"]],
                   on="customer_id", how="left")
            .merge(agents[["agent_id", "agent_name", "team", "experience_level"]], on="agent_id", how="left")
            .merge(departments[["department_id", "department_name"]], on="department_id", how="left")
            .merge(feedback[["ticket_id", "satisfaction_score", "customer_rating", "feedback_category"]],
                   on="ticket_id", how="left"))
    assert len(out) == n, "Join multiplied ticket rows - check key uniqueness"
    out["has_feedback"] = out.customer_rating.notna() | out.satisfaction_score.notna()
    out["is_satisfied"] = np.where(out.satisfaction_score.notna(),
                                   out.satisfaction_score >= config.CSAT_SATISFIED_THRESHOLD, np.nan)
    return out

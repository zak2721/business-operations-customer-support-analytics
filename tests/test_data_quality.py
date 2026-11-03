"""Integrity of the processed datasets on disk (what Power BI, SQL and Streamlit consume)."""
import pandas as pd
import pytest

from src import config
from src.data_validation import validators as v

PKS = {"customers": "customer_id", "agents": "agent_id", "departments": "department_id", "support_tickets": "ticket_id",
       "customer_feedback": "feedback_id", "operations": "operation_id", "agent_performance": "performance_id",
       "business_costs": "cost_id", "calendar": "date"}


@pytest.mark.parametrize("table,pk", PKS.items())
def test_primary_keys_unique_and_not_null(processed, table, pk):
    assert v.is_primary_key(processed[table], pk)
    assert v.exact_duplicates(processed[table]) == 0


def test_foreign_keys_valid(processed):
    p = processed
    assert not v.orphan_keys(p["support_tickets"], "customer_id", p["customers"], "customer_id").any()
    assert not v.orphan_keys(p["support_tickets"], "agent_id", p["agents"], "agent_id").any()
    assert not v.orphan_keys(p["support_tickets"], "department_id", p["departments"], "department_id").any()
    assert not v.orphan_keys(p["customer_feedback"], "ticket_id", p["support_tickets"], "ticket_id").any()
    assert not v.orphan_keys(p["operations"], "department_id", p["departments"], "department_id").any()
    assert not v.orphan_keys(p["agent_performance"], "agent_id", p["agents"], "agent_id").any()


def test_ticket_chronology(processed):
    t = processed["support_tickets"]
    assert not v.chronology_violations(t, "ticket_created_date", "first_response_date").any()
    assert not v.chronology_violations(t, "ticket_created_date", "resolved_date").any()
    assert not v.chronology_violations(t, "first_response_date", "resolved_date").any()


def test_status_and_resolution_date_consistent(processed):
    t = processed["support_tickets"]
    assert set(t.ticket_status) <= set(config.TICKET_STATUSES)
    assert t[~t.ticket_status.isin(config.RESOLVED_STATUSES)].resolved_date.isna().all()
    resolved = t[t.ticket_status.isin(config.RESOLVED_STATUSES)]
    # resolved tickets without a date are exactly the flagged invalid-timestamp ones
    assert (resolved.resolved_date.isna() == resolved.resolution_ts_invalid.astype(bool)).all()


def test_sla_target_matches_priority(processed):
    t = processed["support_tickets"]
    assert (t.sla_target_hours == t.ticket_priority.map(config.SLA_TARGET_HOURS)).all()


def test_scores_in_scale(processed):
    f = processed["customer_feedback"]
    assert f.satisfaction_score.dropna().between(1, 5).all()
    assert f.customer_rating.dropna().between(1, 10).all()
    assert f.ticket_id.is_unique, "more than one survey per ticket would double count CSAT"


def test_costs_and_transactions(processed):
    o, b = processed["operations"], processed["business_costs"]
    assert (o.operational_cost >= 0).all()
    assert (o.successful_transactions + o.failed_transactions == o.total_transactions).all()
    assert ((b.direct_cost + b.indirect_cost - b.total_cost).abs() <= 0.02).all()
    assert (b[["direct_cost", "indirect_cost", "total_cost"]] >= 0).all().all()


def test_canonical_labels(processed):
    t = processed["support_tickets"]
    assert set(t.support_channel) <= {"Email", "Phone", "Live Chat", "Web Portal", "Social Media", "Unknown"}
    assert set(t.ticket_priority) == set(config.SLA_TARGET_HOURS)
    assert set(processed["customers"].customer_segment) == {"Enterprise", "Mid-Market", "Small Business", "Consumer"}


def test_date_ranges_consistent(processed):
    cal = processed["calendar"]
    t = processed["support_tickets"]
    assert cal.date.min() <= processed["customers"].registration_date.min()
    assert cal.date.max() >= t.ticket_created_date.max().normalize()
    assert (cal.date.diff().dropna() == pd.Timedelta(days=1)).all()


def test_quality_report_written_and_improved():
    s = pd.read_json(config.REPORTS_DATA_DIR / "data_quality_summary.json", typ="series")
    assert s.quality_score_after > s.quality_score_before
    assert (config.REPORTS_DATA_DIR / "data_quality_report.md").exists()


def test_enriched_join_does_not_multiply_rows(processed):
    assert len(processed["tickets_enriched"]) == len(processed["support_tickets"])

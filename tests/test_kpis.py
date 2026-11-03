"""KPI engine: known answers on a hand-built frame + invariants on real data."""
import math

import numpy as np
import pandas as pd
import pytest

from src.feature_engineering.features import ticket_features
from src.kpi import kpis as k


def test_volume_kpis(kpi_frame):
    assert k.total_tickets(kpi_frame) == 8
    assert k.open_tickets(kpi_frame) == 1
    assert k.closed_tickets(kpi_frame) == 6
    assert k.cancelled_tickets(kpi_frame) == 1
    assert k.escalated_tickets(kpi_frame) == 1
    assert k.reopened_tickets(kpi_frame) == 1


def test_sla_excludes_open_cancelled_and_invalid(kpi_frame):
    # eligible = T1..T5 ; met = T1, T2, T4
    assert k.sla_compliance_rate(kpi_frame) == 60.0
    assert k.sla_breach_rate(kpi_frame) == 40.0
    assert k.sla_compliance_rate(kpi_frame) + k.sla_breach_rate(kpi_frame) == 100.0


def test_fcr_requires_no_reopen_and_no_escalation(kpi_frame):
    # T3 has FCR resolution type but was reopened -> not FCR
    assert k.fcr_rate(kpi_frame) == 20.0


def test_resolution_rate_vs_sla_vs_fcr_are_distinct(kpi_frame):
    # resolution rate: 6 resolved / 7 non-cancelled
    assert k.resolution_rate(kpi_frame) == pytest.approx(85.71, abs=0.01)
    assert len({k.resolution_rate(kpi_frame), k.sla_compliance_rate(kpi_frame), k.fcr_rate(kpi_frame)}) == 3


def test_resolution_time_only_resolved_eligible(kpi_frame):
    assert k.avg_resolution_hours(kpi_frame) == pytest.approx((2 + 20 + 60 + 10 + 100) / 5)
    assert k.median_resolution_hours(kpi_frame) == 20.0


def test_first_response_ignores_missing(kpi_frame):
    assert k.avg_first_response_hours(kpi_frame) == pytest.approx(np.mean([1, 2, 3, 4, 5, 6]), abs=0.01)


def test_rates_and_backlog(kpi_frame):
    assert k.escalation_rate(kpi_frame) == pytest.approx(100 / 7, abs=0.01)
    assert k.reopen_rate(kpi_frame) == pytest.approx(100 / 6, abs=0.01)
    assert k.repeat_contact_rate(kpi_frame) == 12.5
    assert k.aging_backlog(kpi_frame, 7) == 1


def test_agent_kpis(kpi_frame):
    # 7 tickets with agents across 2 agents
    assert k.tickets_per_agent(kpi_frame) == 3.5
    # known agent & not cancelled: T1,T2,T3,T4,T6,T7 -> resolved 5 of 6
    assert k.agent_productivity_rate(kpi_frame) == pytest.approx(83.33, abs=0.01)


def test_csat_kpis():
    f = pd.DataFrame({"satisfaction_score": [5, 4, 3, np.nan, 1]})
    assert k.avg_csat(f) == 3.25
    assert k.csat_rate(f) == 50.0  # missing score excluded from denominator


def test_operations_kpis():
    o = pd.DataFrame({"total_transactions": [100, 300], "successful_transactions": [90, 294], "failed_transactions": [10, 6],
                      "processing_time_minutes": [10.0, 2.0], "operational_cost": [50.0, 150.0]})
    assert k.operational_success_rate(o) == 96.0
    assert k.operational_failure_rate(o) == 4.0
    assert k.avg_processing_minutes(o) == 4.0           # weighted, not (10+2)/2
    assert k.cost_per_transaction(o) == 0.5
    assert k.operational_efficiency_rate(o) == pytest.approx(384 / 200 * 1000)


def test_safe_division_returns_nan():
    assert math.isnan(k._pct(1, 0))
    empty = pd.DataFrame({"total_transactions": [], "successful_transactions": [], "failed_transactions": [], "operational_cost": []})
    assert math.isnan(k.operational_success_rate(empty))


def test_ticket_feature_engineering():
    t = pd.DataFrame({
        "ticket_id": ["A", "B", "C"], "customer_id": ["X", "X", "Y"],
        "ticket_created_date": pd.to_datetime(["2025-12-01 10:00", "2025-12-05 10:00", "2025-12-30 00:00"]),
        "first_response_date": pd.to_datetime(["2025-12-01 11:30", "2025-12-05 10:30", None]),
        "resolved_date": pd.to_datetime(["2025-12-02 10:00", "2025-12-08 10:00", None]),
        "ticket_status": ["Closed", "Closed", "Open"], "ticket_priority": ["High", "High", "Low"],
        "sla_target_hours": [24, 24, 72], "resolution_type": ["Technical Fix", "Technical Fix", None],
        "reopened_count": [0, 0, 0], "escalation_flag": [0, 0, 0]})
    f = ticket_features(t, snapshot="2025-12-31 00:00:00").set_index("ticket_id")
    assert f.loc["A", "first_response_hours"] == 1.5
    assert f.loc["A", "resolution_hours"] == 24 and f.loc["A", "sla_met"] == 1
    assert f.loc["B", "resolution_hours"] == 72 and f.loc["B", "sla_met"] == 0
    assert bool(f.loc["B", "is_repeat_contact"]) and not bool(f.loc["A", "is_repeat_contact"])
    assert f.loc["C", "ticket_age_days"] == 1.0 and f.loc["C", "aging_bucket"] == "0-2 days"
    assert pd.isna(f.loc["C", "sla_met"])


def test_real_data_kpi_invariants(processed):
    t = processed["tickets_enriched"]
    res = k.compute_all_kpis(t, processed["customer_feedback"], processed["operations"], processed["business_costs"])
    assert res["Total Tickets"] == res["Closed Tickets"] + res["Open Tickets"] + res["Cancelled Tickets"]
    assert res["SLA Compliance Rate (%)"] + res["SLA Breach Rate (%)"] == pytest.approx(100)
    assert res["Operational Success Rate (%)"] + res["Operational Failure Rate (%)"] == pytest.approx(100)
    assert 1 <= res["Avg Customer Satisfaction (1-5)"] <= 5
    assert len(res) >= 30


def test_filters_reduce_scope(processed):
    t = processed["tickets_enriched"]
    flt = k.KPIFilter(start="2025-01-01", end="2025-12-31", channels=["Phone"])
    sub = k.filter_tickets(t, flt)
    assert set(sub.support_channel) == {"Phone"} and sub.ticket_created_date.dt.year.eq(2025).all()

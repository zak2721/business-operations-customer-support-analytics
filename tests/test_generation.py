"""Dataset generation: volumes, keys, logical consistency, reproducibility."""
import pandas as pd

from src.data_generation.generate_data import SupportDataGenerator


def test_full_scale_volumes_meet_requirements(processed):
    assert len(processed["support_tickets"]) >= 20_000
    assert len(processed["customers"]) >= 3_000
    days = (processed["support_tickets"].ticket_created_date.max() - processed["support_tickets"].ticket_created_date.min()).days
    assert days >= 2 * 365


def test_all_tables_generated(small_generated):
    expected = {"customers", "departments", "agents", "support_tickets", "customer_feedback", "operations",
                "agent_performance", "business_costs", "calendar"}
    assert set(small_generated.clean) == expected == set(small_generated.raw)


def test_clean_primary_keys_unique(small_generated):
    pks = {"customers": "customer_id", "agents": "agent_id", "support_tickets": "ticket_id",
           "customer_feedback": "feedback_id", "operations": "operation_id", "business_costs": "cost_id",
           "agent_performance": "performance_id", "departments": "department_id"}
    for table, pk in pks.items():
        assert small_generated.clean[table][pk].is_unique, table


def test_clean_foreign_keys_valid(small_generated):
    c = small_generated.clean
    assert c["support_tickets"].customer_id.isin(c["customers"].customer_id).all()
    assert c["support_tickets"].agent_id.isin(c["agents"].agent_id).all()
    assert c["customer_feedback"].ticket_id.isin(c["support_tickets"].ticket_id).all()
    assert c["agents"].department_id.isin(c["departments"].department_id).all()


def test_ticket_timestamps_chronological(small_generated):
    t = small_generated.clean["support_tickets"]
    assert (t.first_response_date.dropna() >= t.loc[t.first_response_date.notna(), "ticket_created_date"]).all()
    r = t[t.resolved_date.notna()]
    assert (r.resolved_date >= r.ticket_created_date).all()
    assert (r.resolved_date >= r.first_response_date.fillna(r.ticket_created_date)).all()


def test_open_tickets_have_no_resolution_date(small_generated):
    t = small_generated.clean["support_tickets"]
    assert t[t.ticket_status.isin(["Open", "In Progress", "Pending", "Cancelled"])].resolved_date.isna().all()
    assert t[t.ticket_status.isin(["Closed", "Resolved"])].resolved_date.notna().all()


def test_tickets_after_registration_and_hire(small_generated):
    c = small_generated.clean
    t = c["support_tickets"].merge(c["customers"][["customer_id", "registration_date"]]).merge(c["agents"][["agent_id", "hire_date"]])
    assert (t.ticket_created_date >= t.registration_date).all()
    assert (t.ticket_created_date >= t.hire_date).all()


def test_scores_costs_in_range(small_generated):
    c = small_generated.clean
    assert c["customer_feedback"].satisfaction_score.between(1, 5).all()
    assert c["customer_feedback"].customer_rating.between(1, 10).all()
    assert (c["operations"].operational_cost >= 0).all()
    o = c["operations"]
    assert (o.successful_transactions + o.failed_transactions == o.total_transactions).all()


def test_defects_injected_into_raw_only(small_generated):
    m = small_generated.manifest
    raw_t, clean_t = small_generated.raw["support_tickets"], small_generated.clean["support_tickets"]
    assert len(raw_t) == len(clean_t) + m["tickets_exact_duplicates"]
    assert raw_t.duplicated().sum() == m["tickets_exact_duplicates"]
    assert clean_t.duplicated().sum() == 0


def test_reproducible_with_same_seed():
    a = SupportDataGenerator(seed=11, n_customers=150, n_tickets=600).generate()
    b = SupportDataGenerator(seed=11, n_customers=150, n_tickets=600).generate()
    pd.testing.assert_frame_equal(a.clean["support_tickets"], b.clean["support_tickets"])
    pd.testing.assert_frame_equal(a.raw["customer_feedback"], b.raw["customer_feedback"])

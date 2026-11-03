"""Cleaning pipeline: every injected defect is detected exactly; raw data untouched; decisions logged."""
import pandas as pd
import pytest

from src.data_cleaning import cleaners as c
from src.data_cleaning.loader import DataLoadError, load_processed, load_raw
from src.data_cleaning.pipeline import run_cleaning

DETECTION = [  # manifest key -> (table, check)
    ("customers_exact_duplicates", "customers", "exact_duplicates"),
    ("customers_missing_region", "customers", "missing_region"),
    ("customers_missing_clv", "customers", "missing_clv"),
    ("customers_alt_date_format", "customers", "registration_date_format"),
    ("customers_bad_case_segment", "customers", "segment_label_case"),
    ("tickets_exact_duplicates", "support_tickets", "exact_duplicates"),
    ("tickets_resolved_before_created", "support_tickets", "resolved_before_created"),
    ("tickets_missing_first_response", "support_tickets", "resolved_missing_first_response"),
    ("tickets_missing_channel", "support_tickets", "missing_channel"),
    ("tickets_channel_label_variants", "support_tickets", "channel_label_variants"),
    ("tickets_priority_upper_case", "support_tickets", "priority_label_case"),
    ("tickets_wrong_sla_target", "support_tickets", "sla_target_vs_priority"),
    ("tickets_orphan_agent", "support_tickets", "fk_agent"),
    ("feedback_exact_duplicates", "customer_feedback", "exact_duplicates"),
    ("feedback_orphan_ticket", "customer_feedback", "fk_ticket"),
    ("feedback_out_of_range_score", "customer_feedback", "satisfaction_scale"),
    ("operations_negative_cost", "operations", "negative_cost"),
    ("operations_cost_outliers", "operations", "cost_outlier_robust_z"),
    ("operations_missing_processing_time", "operations", "missing_processing_time"),
    ("operations_success_failed_mismatch", "operations", "success_plus_failed_equals_total"),
    ("costs_total_mismatch", "business_costs", "total_equals_components"),
    ("costs_missing_indirect", "business_costs", "missing_indirect_cost"),
    ("performance_sla_over_100", "agent_performance", "sla_rate_0_100"),
]


@pytest.mark.parametrize("key,table,check", DETECTION)
def test_injected_defect_detected_exactly(small_generated, small_cleaned, key, table, check):
    log = small_cleaned[1].to_frame().set_index(["table", "check"]).records_affected
    assert log[(table, check)] == small_generated.manifest[key]


def test_raw_inputs_not_mutated(small_generated):
    before = small_generated.raw["support_tickets"].copy()
    run_cleaning(small_generated.raw)
    pd.testing.assert_frame_equal(before, small_generated.raw["support_tickets"])


def test_every_change_is_logged_with_a_decision(small_cleaned):
    log = small_cleaned[1].to_frame()
    assert log.decision.str.len().gt(10).all()
    assert set(log.action) <= {"removed", "corrected", "imputed", "flagged", "none"}


def test_rows_removed_only_for_duplicates_and_orphans(small_generated, small_cleaned):
    tables, log = small_cleaned
    removed = log.to_frame().query("action == 'removed'").groupby("table").records_affected.sum()
    for name in ("customers", "support_tickets", "customer_feedback", "operations"):
        diff = len(small_generated.raw[name]) - len(tables[name])
        assert diff == removed.get(name, 0), name


def test_imputed_values_are_flagged(small_cleaned):
    t = small_cleaned[0]
    assert t["customers"].clv_imputed.sum() > 0 and t["customers"].customer_lifetime_value.notna().all()
    assert t["operations"].processing_time_imputed.sum() > 0 and t["operations"].processing_time_minutes.notna().all()
    o = t["operations"]
    assert (o.loc[o.cost_outlier, "operational_cost"] < o.loc[o.cost_outlier, "operational_cost_original"]).all()


def test_satisfaction_never_imputed(small_cleaned):
    f = small_cleaned[0]["customer_feedback"]
    assert f.satisfaction_score.isna().sum() > 0
    assert f.satisfaction_score.dropna().between(1, 5).all()


def test_parse_mixed_dates():
    s = pd.Series(["2024-02-29", "05-Mar-2023", "not a date"])
    out = c.parse_mixed_dates(s)
    assert out.iloc[0] == pd.Timestamp("2024-02-29") and out.iloc[1] == pd.Timestamp("2023-03-05")
    assert pd.isna(out.iloc[2])


def test_channel_map_covers_all_variants():
    for v in ["email", "E-mail", "EMAIL", "chat", "live chat", "LiveChat", "phone", "web", "Web portal", "social", "Social"]:
        assert v.strip().lower() in c.CHANNEL_MAP


def test_loader_reads_files_and_errors_clearly(tmp_path):
    assert len(load_raw("departments")) == 6
    assert "ticket_created_date" in load_processed("support_tickets").select_dtypes("datetime").columns
    with pytest.raises(DataLoadError):
        load_processed("support_tickets", tmp_path)

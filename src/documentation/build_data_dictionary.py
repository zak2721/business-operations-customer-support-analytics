"""Generate docs/data_dictionary.md from the processed datasets.

Types, null counts and example values are read from the data; descriptions
come from the DESCRIPTIONS mapping below (the single place they are maintained).
"""
from __future__ import annotations

import pandas as pd

from src import config
from src.data_cleaning.loader import load_processed

DESCRIPTIONS = {
    # customers
    "customer_id": "Customer key (CUS-nnnnn)", "customer_name": "Synthetic person/company name (Faker); not shown in apps",
    "customer_segment": "Enterprise / Mid-Market / Small Business / Consumer", "customer_region": "Sales region (derived from country when missing in raw)",
    "customer_country": "Country", "customer_type": "Business or Individual", "registration_date": "Date the customer account was created",
    "customer_status": "Active / Inactive / Churned at snapshot", "customer_lifetime_value": "Lifetime value in USD",
    "clv_imputed": "TRUE if CLV was missing in raw and imputed with the segment median",
    # departments / agents
    "department_id": "Department key (DEP-nn)", "department_name": "Department name", "department_manager": "Synthetic manager name",
    "department_location": "Primary site", "operational_budget": "Annual staffing & overhead budget (USD)",
    "agent_id": "Agent key (AGT-nnn); NULL on 15 tickets whose raw agent did not exist", "agent_name": "Synthetic agent name",
    "team": "Team within department", "hire_date": "Hire date", "experience_level": "Junior / Mid-Level / Senior / Lead",
    "employment_status": "Active / On Leave / Terminated", "shift": "Morning / Afternoon / Night", "location": "Work location",
    # tickets
    "ticket_id": "Ticket key (TCK-nnnnnn)", "ticket_created_date": "Creation timestamp", "first_response_date": "First agent response timestamp (NULL if none yet)",
    "resolved_date": "Resolution timestamp (NULL unless Closed/Resolved with a valid time)", "ticket_category": "Top-level reason (8 values)",
    "ticket_subcategory": "Detailed reason", "ticket_priority": "Critical / High / Medium / Low", "ticket_status": "Open / In Progress / Pending / Resolved / Closed / Cancelled",
    "support_channel": "Email / Phone / Live Chat / Web Portal / Social Media / Unknown", "resolution_type": "How the ticket was resolved",
    "reopened_count": "Number of times reopened", "escalation_flag": "1 if escalated", "sla_target_hours": "Resolution SLA target: Critical 8, High 24, Medium 48, Low 72",
    "agent_unknown": "Raw agent_id referenced a non-existent agent", "resolution_ts_invalid": "Raw resolution time preceded creation; excluded from time KPIs",
    "first_response_missing": "Resolved ticket with no first-response timestamp",
    "first_response_hours": "Hours from creation to first response", "resolution_hours": "Hours from creation to resolution",
    "is_cancelled": "Status = Cancelled", "is_resolved": "Status in (Closed, Resolved)", "is_unresolved": "Status in (Open, In Progress, Pending)",
    "sla_eligible": "Resolved with a valid resolution timestamp (SLA/FCR denominator)", "sla_met": "1 if resolution_hours <= sla_target_hours (eligible only)",
    "sla_breached": "1 if resolution_hours > sla_target_hours (eligible only)", "frt_target_hours": "First-response target: Critical 1, High 4, Medium 8, Low 24",
    "frt_met": "1 if first response within target", "is_reopened": "reopened_count > 0", "is_escalated": "escalation_flag = 1",
    "is_fcr": "First-contact resolution: eligible, resolution_type = First Contact Resolution, never reopened or escalated",
    "created_date": "Creation date", "created_year": "Creation year", "created_month": "Creation month (YYYY-MM)", "created_quarter": "Creation quarter",
    "created_hour": "Hour of creation", "created_dayname": "Weekday of creation", "created_weekday": "Created Mon-Fri", "resolved_month": "Resolution month",
    "ticket_age_days": "Age at snapshot (31 Dec 2025) for unresolved tickets", "aging_bucket": "Age band of open tickets",
    "aging_sla_exposed": "Open ticket already older than its SLA target", "resolution_bucket": "Resolution-time band",
    "days_since_prev_ticket": "Days since the same customer's previous ticket", "customer_ticket_seq": "Nth ticket of this customer",
    "is_repeat_contact": "Created within 7 days of the customer's previous ticket",
    # feedback
    "feedback_id": "Survey key (FBK-nnnnnn)", "feedback_date": "Survey timestamp", "satisfaction_score": "CSAT 1-5 (NULL if missing or invalid in raw)",
    "customer_rating": "Rating 1-10", "feedback_category": "Theme of the feedback", "customer_comment": "Free-text comment (synthetic, often empty)",
    "satisfaction_score_invalid": "Raw score was outside 1-5",
    # operations
    "operation_id": "Operation-day key (OPS-nnnnnn)", "operation_date": "Day", "operation_type": "Operation family", "process_name": "Process (13 values)",
    "total_transactions": "Transactions processed", "successful_transactions": "Transactions completed successfully", "failed_transactions": "Failed transactions",
    "processing_time_minutes": "Average minutes per transaction that day", "operational_cost": "Variable processing cost (USD)",
    "operational_status": "Normal (<5% fail) / Degraded (5-10%) / Critical (>=10%)", "cost_sign_corrected": "Raw cost was negative (sign error corrected)",
    "cost_outlier": "Raw cost was an extreme outlier and replaced", "operational_cost_original": "Raw cost before outlier treatment",
    "processing_time_imputed": "Processing time was missing and imputed", "success_rate": "% successful", "failure_rate": "% failed",
    "cost_per_transaction": "Cost / transactions", "total_processing_hours": "processing_time_minutes x transactions / 60", "operation_month": "YYYY-MM",
    # performance & costs
    "performance_id": "Agent-month key", "performance_date": "Month end", "tickets_assigned": "Tickets created that month for the agent",
    "tickets_resolved": "Tickets the agent resolved that month", "average_response_time": "Avg first response hours (tickets created that month)",
    "average_resolution_time": "Avg resolution hours (tickets resolved that month)", "customer_satisfaction_score": "Avg CSAT of tickets resolved that month",
    "sla_compliance_rate": "% of that month's resolved tickets within SLA", "workload_hours": "Logged handling + admin hours",
    "cost_id": "Cost line key", "cost_date": "Month start", "cost_category": "Personnel / Technology & Software / Facilities / Training & Development / Outsourcing / Telecommunications",
    "direct_cost": "Directly attributable cost (USD)", "indirect_cost": "Allocated overhead (USD)", "total_cost": "direct_cost + indirect_cost",
    # calendar
    "date": "Calendar day", "year": "Year", "quarter": "Quarter 1-4", "month": "Month 1-12", "month_name": "Month name", "week": "ISO week",
    "day": "Day of month", "day_name": "Weekday name", "weekday_flag": "1 = Mon-Fri", "year_month": "YYYY-MM", "quarter_label": "YYYY-Qn",
}
TABLES = {
    "customers": "One row per customer.", "departments": "One row per support department.", "agents": "One row per support agent.",
    "support_tickets": "One row per ticket, with engineered analytical features.", "customer_feedback": "One survey per ticket (max).",
    "operations": "One row per process per day.", "agent_performance": "One row per agent per month (derived from tickets).",
    "business_costs": "One row per department, month and cost category.", "calendar": "Date dimension 2021-01-01 to 2025-12-31.",
}


def main() -> None:
    md = ["# Data Dictionary", "", "Generated by `src/documentation/build_data_dictionary.py` from `data/processed/`. "
          "Raw files in `data/raw/` have the same base columns (before cleaning, with injected defects); engineered columns exist only in processed data.",
          "", "> All data is synthetic. Names are produced by Faker and do not refer to real people or companies.", ""]
    for name, desc in TABLES.items():
        df = load_processed(name)
        md += [f"## {name}", "", f"{desc} **{len(df):,} rows.** File: `data/processed/{name}.csv`", "",
               "| Column | Type | Nulls | Example | Description |", "|---|---|---:|---|---|"]
        for c in df.columns:
            ex = df[c].dropna()
            ex = str(ex.iloc[0])[:28] if len(ex) else ""
            md.append(f"| `{c}` | {df[c].dtype} | {int(df[c].isna().sum()):,} | {ex} | {DESCRIPTIONS.get(c, '')} |")
        md.append("")
    md += ["## tickets_enriched", "", "`support_tickets` joined (left, 1:1) with customer segment/region, agent name/team/experience, "
           "department name and the ticket's survey score. Used by notebooks, Streamlit and the prototype.", "",
           "## Power BI star schema", "", "`data/processed/powerbi/` — see [`powerbi/data_model.md`](../powerbi/data_model.md)."]
    (config.PROJECT_ROOT / "docs" / "data_dictionary.md").write_text("\n".join(md) + "\n")
    print("docs/data_dictionary.md written")


if __name__ == "__main__":
    main()

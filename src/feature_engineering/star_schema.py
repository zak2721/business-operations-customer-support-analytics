"""Build the Power BI star schema (facts + conformed dimensions) from processed data.

Run:
    python -m src.feature_engineering.star_schema

Output: data/processed/powerbi/*.csv - one file per model table. Power Query
scripts in powerbi/power_query/ load these files directly.
"""
from __future__ import annotations

import pandas as pd

from src import config
from src.data_cleaning.loader import load_processed

OUT_DIR = config.PROCESSED_DIR / "powerbi"


def build_star_schema() -> dict[str, pd.DataFrame]:
    t = load_processed("support_tickets")
    cust = load_processed("customers")
    agents = load_processed("agents")
    deps = load_processed("departments")
    fb = load_processed("customer_feedback")
    ops = load_processed("operations")
    perf = load_processed("agent_performance")
    costs = load_processed("business_costs")
    cal = load_processed("calendar")

    dim_date = cal.rename(columns={"date": "Date"})
    dim_date["DateKey"] = dim_date.Date.dt.strftime("%Y%m%d").astype(int)
    dim_date["MonthStart"] = dim_date.Date.values.astype("datetime64[M]")
    dim_date["IsWeekend"] = 1 - dim_date.weekday_flag

    dim_customer = cust.drop(columns=["clv_imputed"])
    dim_agent = agents.merge(deps[["department_id", "department_name"]], on="department_id", how="left")
    dim_department = deps

    cats = t[["ticket_category", "ticket_subcategory"]].drop_duplicates().sort_values(["ticket_category", "ticket_subcategory"])
    cats.insert(0, "category_key", range(1, len(cats) + 1))
    dim_category = cats.reset_index(drop=True)

    chan = pd.DataFrame({"support_channel": ["Email", "Phone", "Live Chat", "Web Portal", "Social Media", "Unknown"]})
    chan["channel_type"] = chan.support_channel.map({"Phone": "Real-time", "Live Chat": "Real-time", "Email": "Asynchronous",
                                                     "Web Portal": "Asynchronous", "Social Media": "Asynchronous", "Unknown": "Unknown"})
    chan.insert(0, "channel_key", range(1, len(chan) + 1))

    pri = pd.DataFrame({"ticket_priority": ["Critical", "High", "Medium", "Low"], "priority_sort": [1, 2, 3, 4]})
    pri["sla_target_hours"] = pri.ticket_priority.map(config.SLA_TARGET_HOURS)
    pri["frt_target_hours"] = pri.ticket_priority.map(config.FRT_TARGET_HOURS)
    pri.insert(0, "priority_key", range(1, len(pri) + 1))

    proc = ops[["department_id", "operation_type", "process_name"]].drop_duplicates().sort_values("process_name")
    proc.insert(0, "process_key", range(1, len(proc) + 1))
    dim_process = proc.reset_index(drop=True)

    fact_t = (t.merge(dim_category, on=["ticket_category", "ticket_subcategory"], how="left")
               .merge(chan[["channel_key", "support_channel"]], on="support_channel", how="left")
               .merge(pri[["priority_key", "ticket_priority"]], on="ticket_priority", how="left"))
    fact_t["created_date"] = fact_t.ticket_created_date.dt.normalize()
    fact_t["resolved_date_only"] = fact_t.resolved_date.dt.normalize()
    keep = ["ticket_id", "customer_id", "agent_id", "department_id", "category_key", "channel_key", "priority_key",
            "created_date", "resolved_date_only", "ticket_created_date", "first_response_date", "resolved_date",
            "ticket_status", "resolution_type", "reopened_count", "escalation_flag", "sla_target_hours",
            "first_response_hours", "resolution_hours", "is_resolved", "is_unresolved", "is_cancelled", "sla_eligible",
            "sla_met", "is_fcr", "is_reopened", "is_repeat_contact", "ticket_age_days", "aging_bucket",
            "resolution_bucket", "created_hour", "agent_unknown", "resolution_ts_invalid"]
    fact_t = fact_t[keep]
    for b in ["is_resolved", "is_unresolved", "is_cancelled", "sla_eligible", "is_fcr", "is_reopened",
              "is_repeat_contact", "agent_unknown", "resolution_ts_invalid"]:
        fact_t[b] = fact_t[b].astype(bool).astype(int)
    fact_t["sla_met"] = fact_t.sla_met.astype("Float64").astype("Int64")

    # Ticket attributes are copied onto the feedback fact (degenerate attributes)
    # so CSAT can be sliced by category/channel/priority and plotted against
    # response time WITHOUT a fact-to-fact relationship in the model.
    fact_fb = fb.merge(t[["ticket_id", "agent_id", "department_id", "support_channel", "ticket_priority",
                          "ticket_category", "ticket_subcategory", "first_response_hours", "resolution_hours",
                          "sla_met"]], on="ticket_id", how="left")
    fact_fb = fact_fb.merge(dim_category, on=["ticket_category", "ticket_subcategory"], how="left") \
                     .drop(columns=["ticket_category", "ticket_subcategory"])
    fact_fb["sla_met"] = fact_fb.sla_met.astype("Float64").astype("Int64")
    fact_fb = (fact_fb.merge(chan[["channel_key", "support_channel"]], on="support_channel", how="left")
                      .merge(pri[["priority_key", "ticket_priority"]], on="ticket_priority", how="left")
                      .drop(columns=["support_channel", "ticket_priority"]))
    fact_fb["feedback_date_only"] = fact_fb.feedback_date.dt.normalize()

    fact_ops = ops.merge(dim_process[["process_key", "process_name"]], on="process_name", how="left")
    fact_perf = perf.merge(agents[["agent_id", "department_id"]], on="agent_id", how="left")
    fact_costs = costs

    tables = {
        "DimDate": dim_date, "DimCustomer": dim_customer, "DimAgent": dim_agent, "DimDepartment": dim_department,
        "DimTicketCategory": dim_category, "DimSupportChannel": chan, "DimPriority": pri, "DimProcess": dim_process,
        "FactSupportTickets": fact_t, "FactCustomerFeedback": fact_fb, "FactAgentPerformance": fact_perf,
        "FactOperations": fact_ops, "FactBusinessCosts": fact_costs,
    }
    # integrity: every fact FK must resolve to its dimension
    assert fact_t.category_key.notna().all() and fact_t.channel_key.notna().all() and fact_t.priority_key.notna().all()
    assert fact_ops.process_key.notna().all()
    return tables


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, df in build_star_schema().items():
        df.to_csv(OUT_DIR / f"{name}.csv", index=False, date_format="%Y-%m-%d %H:%M:%S")
        print(f"{name:<24}{len(df):>8} rows  {df.shape[1]:>3} cols")


if __name__ == "__main__":
    main()

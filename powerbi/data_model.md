# Power BI Data Model

Star schema built by `python -m src.feature_engineering.star_schema` into `data/processed/powerbi/` and loaded by the Power Query scripts in `powerbi/power_query/`.

> **Status:** the model is fully specified and its tables, M scripts, DAX and theme are generated and validated in Python/SQL. A `.pbix` file is **not** included: it must be assembled in Power BI Desktop (Windows) following [`implementation_guide.md`](implementation_guide.md). No claim is made that a finished PBIX exists.

## Diagram

```
                         ┌──────────────┐
                         │   DimDate    │ (marked as date table)
                         └──────┬───────┘
     created_date (active) ┌────┼────────┬──────────────┬───────────────┬────────────────┐
  resolved_date_only (inact)│    │        │              │               │                │
                    ┌───────▼────▼──┐ ┌───▼──────────┐ ┌─▼────────────┐ ┌▼─────────────┐ ┌▼──────────────┐
DimCustomer ───────►│FactSupport    │ │FactCustomer  │ │FactAgent     │ │FactOperations│ │FactBusiness   │
DimAgent ──────────►│Tickets        │ │Feedback      │ │Performance   │ │              │ │Costs          │
DimTicketCategory ─►│ (ticket)      │ │ (survey)     │ │ (agent-month)│ │ (process-day)│ │ (dept-month-  │
DimSupportChannel ─►│               │ │              │ │              │ │              │ │  category)    │
DimPriority ───────►│               │ │              │ │              │ │◄── DimProcess│ │               │
DimDepartment ─────►└───────────────┘ └──────────────┘ └──────────────┘ └──────────────┘ └───────────────┘
   (DimDepartment also filters Feedback, AgentPerformance, Operations, BusinessCosts)
```

## Tables

| Table | Type | Grain | Primary key | Rows |
|---|---|---|---|---:|
| FactSupportTickets | Fact | one ticket | ticket_id | 24,000 |
| FactCustomerFeedback | Fact | one survey (max 1 per ticket) | feedback_id | 12,466 |
| FactAgentPerformance | Fact | agent × month | performance_id | 1,984 |
| FactOperations | Fact | process × day | operation_id | 14,248 |
| FactBusinessCosts | Fact | department × month × cost category | cost_id | 1,296 |
| DimDate | Dimension | day (2021-01-01 … 2025-12-31) | Date | 1,826 |
| DimCustomer | Dimension | customer | customer_id | 3,200 |
| DimAgent | Dimension | agent | agent_id | 60 |
| DimDepartment | Dimension | department | department_id | 6 |
| DimTicketCategory | Dimension | category × subcategory | category_key | 34 |
| DimSupportChannel | Dimension | channel (+ Unknown) | channel_key | 6 |
| DimPriority | Dimension | priority (with sort, SLA & FRT targets) | priority_key | 4 |
| DimProcess | Dimension | operational process | process_key | 13 |
| _Measures | Measure table | — | — | — |

## Relationships

All relationships are **many-to-one (*:1), single-direction** (dimension filters fact). No many-to-many and no bidirectional filters.

| From (many) | To (one) | Active | Notes |
|---|---|---|---|
| FactSupportTickets[created_date] | DimDate[Date] | ✅ | cohort view: tickets by creation date |
| FactSupportTickets[resolved_date_only] | DimDate[Date] | ❌ inactive | throughput view via `USERELATIONSHIP` |
| FactSupportTickets[customer_id] | DimCustomer[customer_id] | ✅ | |
| FactSupportTickets[agent_id] | DimAgent[agent_id] | ✅ | blank agent_id (15 flagged tickets) → "(Blank)" member |
| FactSupportTickets[department_id] | DimDepartment[department_id] | ✅ | |
| FactSupportTickets[category_key] | DimTicketCategory[category_key] | ✅ | |
| FactSupportTickets[channel_key] | DimSupportChannel[channel_key] | ✅ | |
| FactSupportTickets[priority_key] | DimPriority[priority_key] | ✅ | |
| FactCustomerFeedback[feedback_date_only] | DimDate[Date] | ✅ | CSAT by survey date |
| FactCustomerFeedback[customer_id / agent_id / department_id / category_key / channel_key / priority_key] | matching dims | ✅ | ticket attributes copied onto the survey row |
| FactAgentPerformance[performance_date] | DimDate[Date] | ✅ | month-end date |
| FactAgentPerformance[agent_id] | DimAgent[agent_id] | ✅ | |
| FactAgentPerformance[department_id] | DimDepartment[department_id] | ✅ | |
| FactOperations[operation_date] | DimDate[Date] | ✅ | |
| FactOperations[department_id] | DimDepartment[department_id] | ✅ | |
| FactOperations[process_key] | DimProcess[process_key] | ✅ | |
| FactBusinessCosts[cost_date] | DimDate[Date] | ✅ | month-start date |
| FactBusinessCosts[department_id] | DimDepartment[department_id] | ✅ | |

**Deliberately not related:** `DimAgent → DimDepartment` (DimAgent carries `department_name` as an attribute instead). Relating it would create two filter paths from DimDepartment to the ticket fact (ambiguity). Likewise `FactCustomerFeedback → FactSupportTickets` is **not** related (fact-to-fact): the feedback fact carries the ticket attributes it needs (category, channel, priority, first_response_hours, resolution_hours, sla_met).

## Preventing double counting

| Risk | Control |
|---|---|
| Duplicate tickets / surveys | Removed in cleaning; PK uniqueness tested (`tests/test_data_quality.py`) |
| A ticket with several surveys inflating CSAT | Cleaning keeps the latest survey per ticket; SQL enforces `UNIQUE(ticket_id)` |
| Joining tickets to feedback in visuals | No fact-to-fact relationship; CSAT measures read FactCustomerFeedback only |
| Agent performance vs ticket counts disagreeing | Agent page uses ticket fact for volume/SLA, performance fact only for workload/AHT |
| Averages of percentages | All rates are `DIVIDE(sum, sum)`; processing time is transaction-weighted |
| Departments via two paths | DimAgent not related to DimDepartment |

## Date handling

* `DimDate` is marked as the date table (`Date` column) so `DATEADD`, `SAMEPERIODLASTYEAR`, `TOTALYTD` work.
* Ticket KPIs default to **creation-date** semantics (cohort). Use the "by Resolved Date" measures for throughput.
* CSAT uses **feedback date**; operations/costs use their own dates. A single date slicer on DimDate filters all facts consistently.
* Backlog/aging measures describe state at the **31-Dec-2025 snapshot** for tickets created in the selected period.

## Model assumptions

1. Snapshot date = 2025-12-31 23:59:59; open tickets' age is measured to it.
2. Flags are 0/1 integers so they aggregate with `SUM`.
3. `sla_met` is blank for unresolved/cancelled tickets and for the 25 tickets with invalid resolution timestamps.
4. Operations "Region" slicer uses `DimDepartment[department_location]` (operations have no customer region).
5. Customer names are synthetic; the report shows IDs/segments by default (no PII on visuals).

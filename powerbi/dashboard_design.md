# Power BI Dashboard Design

Six report pages, 16:9 canvas (1280 × 720), one shared layout grid and theme (`powerbi/theme/support_analytics_theme.json`).
A working, data-driven **HTML prototype** of this exact design (built from the real processed data) is in `powerbi/dashboard_prototype/index.html`; it is a design reference, not a Power BI file.

## Visual identity

| Token | Value | Use |
|---|---|---|
| Page background | `#F4F5F7` | canvas |
| Card / visual background | `#FFFFFF`, 1px border `#E6E5E0`, radius 8 | every visual |
| Header band | `#0D366B` (navy) with white title | page header & navigation |
| Series 1-8 | `#2a78d6 #eb6834 #1baf7a #eda100 #e87ba4 #008300 #6250d6 #e34948` | categorical, assigned in fixed order |
| Sequential | `#cde2fb → #0d366b` | heatmaps, magnitude |
| Status | good `#0ca30c` · warning `#fab219` · critical `#d03b3b` | SLA / success states only, always with a label |
| Typeface | Segoe UI / Segoe UI Semibold | titles 12pt, labels 10pt, KPI values 24-26pt |

Rules: one y-axis per chart (no dual axes); legends for ≥ 2 series; direct labels only where selective; status colours never reused as series colours; colour never the only carrier of meaning (cards show ▲/▼ + text).

## Layout grid (all pages)

```
┌────────────────────────────────────────────────────────────────────────────┐
│ HEADER 56px: page title · period label ([Selected Period Label]) · nav pills│
├──────────┬─────────────────────────────────────────────────────────────────┤
│ SLICER   │ KPI CARD ROW (4-8 cards, 96px)                                  │
│ PANEL    ├────────────────────────────┬────────────────────────────────────┤
│ 200px    │ PRIMARY CHART (trend)      │ SECONDARY CHART                    │
│ (date,   │                            │                                    │
│ dept,    ├──────────────┬─────────────┼──────────────┬─────────────────────┤
│ ...)     │ CHART        │ CHART       │ CHART        │ CHART / TABLE       │
└──────────┴──────────────┴─────────────┴──────────────┴─────────────────────┘
```

* Navigation: page-navigator buttons in the header (Overview · Support · Experience · Agents · Operations · SLA).
* Sync slicers: Date and Department synced across all pages; page-specific slicers stay local.
* Tooltips: a report-page tooltip **"Ticket KPI tooltip"** (240×160) showing Tickets, SLA %, Avg Resolution, CSAT for whatever is hovered; enabled on every category chart.
* Drill-through: **"Agent Detail"** (target: DimAgent[agent_name]) and **"Department Detail"** (target: DimDepartment[department_name]) hidden pages with KPI cards + monthly trend + category mix. Right-click any agent/department point → Drill through.
* Bookmarks: "Reset filters" button on every page.

## Page 1 — Executive Business Overview

**Purpose:** one-screen health check for management.

| Zone | Visual | Fields / measures |
|---|---|---|
| Cards (8) | Card (new) with reference label vs previous month | Total Tickets · Open Tickets · Avg Resolution Time (h) · SLA Compliance Rate · Avg Customer Satisfaction · Total Operational Cost · Operational Success Rate · First Contact Resolution Rate |
| Primary | Line chart | DimDate[MonthStart] × Total Tickets, Tickets 3M Moving Avg |
| Secondary | 100% stacked bar | Successful vs Failed Transactions by year (status colours good/critical) |
| Row 2 | Column chart | Total Tickets by DimPriority[ticket_priority] (sorted by priority_sort) |
| Row 2 | Line chart | Avg Customer Satisfaction by month |
| Row 2 | Bar chart | SLA Compliance Rate by department, constant line at 0.85 target |
| Row 2 | Bar chart | Departmental Cost + Total Operational Cost by department (two visuals side by side, not dual axis) |
| Slicers | Date range, Department, Region (DimCustomer[customer_region]), Channel, Priority | |

## Page 2 — Customer Support Performance

| Zone | Visual | Fields / measures |
|---|---|---|
| Cards (6) | Total Tickets · Resolved Tickets · Open Tickets · Avg First Response Time (h) · Avg Resolution Time (h) · First Contact Resolution Rate |
| Primary | Column chart | Total Tickets by month |
| Charts | Bar | Total Tickets by DimTicketCategory[ticket_category] (drill down to subcategory) |
| | Column | Total Tickets by priority |
| | Donut-free bar | Total Tickets by ticket_status |
| | Bar | Avg Resolution Time (h) by category |
| | Bar | Total Tickets by channel |
| | Line | Open tickets at month end (precomputed backlog table, or Ticket Backlog by MonthStart) |
| | Matrix | Reopened Tickets, Reopen Rate by category × priority with data bars |
| Slicers | Date, Category, Priority, Status, Channel | |

## Page 3 — Customer Experience & Satisfaction

| Zone | Visual | Fields / measures |
|---|---|---|
| Cards (4) | Avg Customer Satisfaction · Customer Satisfaction Rate · Repeat Contact Rate · Escalation Rate (+ Customer Satisfaction Change as subtitle) |
| Primary | Line | Avg Customer Satisfaction by month |
| Charts | Bar | CSAT by channel |
| | Bar | CSAT by department |
| | Bar | CSAT by category |
| | Column | CSAT by first-response band (calculated column on FactCustomerFeedback: `FRT Band` from first_response_hours) |
| | Column | CSAT by resolution band |
| | Bar | Survey Responses by feedback_category |
| Slicers | Date, Customer Segment, Region, Channel, Category | |

`FRT Band` calculated column (FactCustomerFeedback):
```DAX
FRT Band = SWITCH(TRUE(), ISBLANK([first_response_hours]), "No response",
  [first_response_hours] < 0.25, "1 <15 min", [first_response_hours] < 1, "2 15-60 min",
  [first_response_hours] < 4, "3 1-4 h", [first_response_hours] < 8, "4 4-8 h",
  [first_response_hours] < 24, "5 8-24 h", "6 24 h+")
```

## Page 4 — Agent Performance & Productivity

| Zone | Visual | Fields / measures |
|---|---|---|
| Cards (6) | Total Agents · Tickets Resolved · Tickets per Agent · Average Handling Time (min) · Agent SLA Compliance · Average Agent Satisfaction Score |
| Charts | Bar (Top N = 15) | Tickets Resolved by DimAgent[agent_name] |
| | Table | Agent Productivity Rank, agent, Tickets Resolved, Agent SLA Compliance (conditional icons), Avg CSAT |
| | Bar | Agent SLA Compliance by agent (constant line at company rate) |
| | Bar | Avg Resolution Time (h) by agent |
| | Column | Workload Hours by month, small multiples by experience level |
| | Scatter | Agent SLA Compliance (x) vs Average Agent Satisfaction Score (y), size = Tickets Resolved, details = agent |
| | Clustered bar | Tickets Assigned vs Tickets Resolved by agent |
| Slicers | Department, Team, Agent, Experience Level, Date | |

## Page 5 — Business Operations & Cost Analysis

| Zone | Visual | Fields / measures |
|---|---|---|
| Cards (6) | Total Transactions · Successful Transactions · Operational Success Rate · Total Operational Cost · Average Cost per Transaction · Average Processing Time (min) |
| Charts | Line | Total Transactions by month |
| | 100% stacked column | Successful vs Failed by month |
| | Bar | Total Operational Cost by department |
| | Bar | Departmental Cost by FactBusinessCosts[cost_category] |
| | Bar | Average Processing Time (min) by DimProcess[process_name] |
| | Line | Average Cost per Transaction by month |
| | Matrix | Department × (Transactions, Success Rate, Failure Rate, Cost/Txn, Budget Utilisation) with conditional formatting |
| Slicers | Date, Department, Operation Type, Process, Region (department location) | |

## Page 6 — SLA, Service Quality & Operational Bottlenecks

| Zone | Visual | Fields / measures |
|---|---|---|
| Cards (6) | SLA Compliance Rate (colour = SLA Status Colour) · SLA Breach Rate · Escalated Tickets · Reopened Tickets · Aging Ticket Backlog · First Contact Resolution Rate |
| Charts | Line | SLA Compliance Rate by month with constant line at target |
| | Column | SLA Breached Tickets by priority |
| | Bar | SLA Breach Rate by department |
| | Column | Open Tickets by aging_bucket (sorted 0-2 → 60+) |
| | Bar | Escalated Tickets by category (escalation reasons proxy) |
| | Bar | Reopened Tickets by category |
| | Column | Avg Resolution Time (h) by priority with SLA target as constant lines |
| | Matrix | Process × Failure Rate, processing time, degraded-day share (bottleneck table) with red-amber-green icons |
| Slicers | Date, Department, Priority, Category, Channel | |

## Accessibility checklist

- [ ] Alt text on every visual (describe the takeaway, not the chart type)
- [ ] Tab order set top-left → bottom-right
- [ ] No information conveyed by colour alone (labels/icons on status)
- [ ] Minimum 10pt text; contrast ≥ 4.5:1 for text
- [ ] "Show as table" works on every visual (no custom visuals required)

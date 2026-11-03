# Project Overview

## The business problem

Support and operations leaders typically see their data in silos: ticket queues in a help-desk tool, surveys in a survey tool, transaction logs in operational systems, and budgets in finance spreadsheets. They cannot answer cross-cutting questions such as *"Is the Billing SLA drop a staffing problem, a demand problem or a process problem?"*, and the KPIs they do see are often computed inconsistently (averages of percentages, open tickets mixed into SLA rates, double-counted surveys).

## What this project delivers

A single, reproducible analytics solution that integrates nine datasets and answers those questions consistently across Python, SQL, Power BI and a web app.

| Layer | Deliverable | Location |
|---|---|---|
| Data | Synthetic generator (24,000 tickets, 3,200 customers, 3 years) with injected defects | `src/data_generation/`, `data/raw/` |
| Cleaning | Reusable validation + cleaning modules, issue log, before/after quality score | `src/data_cleaning/`, `src/data_validation/`, `data/reports/` |
| KPIs | 30 documented KPIs implemented once per layer and cross-checked | `src/kpi/`, `docs/KPI_definitions.md` |
| EDA | 7 executed notebooks, 50 charts | `notebooks/`, `visualizations/` |
| SQL | PostgreSQL 16 schema with business-rule constraints, 46 analytical queries, 8 DQ checks, 11 views | `sql/`, `docs/SQL_documentation.md` |
| BI | Star schema, 71 DAX measures, Power Query M, theme, 6-page design, interactive HTML prototype | `powerbi/` |
| App | 8-page Streamlit application with filters and downloads | `streamlit_app/` |
| Advanced | Statistical tests, root-cause analysis, leakage-safe SLA-breach model | `src/analytics/` |
| Insights | 25 data-driven insights with actions and KPIs to monitor | `reports/` |
| Quality | 100 automated tests | `tests/` |

## Key business questions answered

1. Which channels respond slowest, and how much does that cost in satisfaction?
2. Which departments, priorities and categories breach SLA most, and is it getting worse?
3. What explains the 2025 Billing deterioration?
4. Which agents are overloaded or need coaching, and does experience matter?
5. Which operational processes are bottlenecks, and why is cost rising?
6. How old is the backlog and what is at risk right now?
7. Can SLA breaches be anticipated when a ticket is created?

See [`reports/executive_summary.md`](../reports/executive_summary.md) for the answers.

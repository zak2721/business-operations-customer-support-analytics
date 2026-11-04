# Business Operations & Customer Support Analytics Dashboard

**Role:** Data Analyst · BI Developer · Python & SQL
**Tools:** Python (pandas, scikit-learn, statsmodels), PostgreSQL, Power BI (DAX, Power Query), Streamlit, Plotly
**Type:** Portfolio project, built on a realistic synthetic dataset (24,000 tickets, 3,200 customers, 3 years)

---

## Project Summary

I built an end-to-end analytics solution that lets a support-driven business monitor **customer service performance, SLA compliance, customer satisfaction, agent productivity, operational efficiency and operating cost** in one place, with the same KPI definitions in Python, SQL and Power BI.

It goes beyond dashboards. It explains *why* targets are missed (root-cause analysis, statistical tests), flags tickets likely to breach SLA when they are created, and turns the findings into prioritised recommendations with KPIs to track.

## Business Challenges Addressed

- Ticket, survey, operations and cost data live in separate systems, so cross-cutting questions go unanswered.
- KPIs are computed inconsistently: open tickets inside SLA rates, averages of percentages, duplicate surveys inflating CSAT.
- Managers see *that* SLA or satisfaction dropped, but not *where* or *why*.
- Backlog, workload and bottlenecks surface only after customers complain.
- Raw data is messy: duplicates, inconsistent labels, impossible timestamps, outliers.

## My Analytical Approach

1. **Data generation & preparation.** I designed a realistic data model (9 related tables) and generated 3 years of data with real business mechanics (seasonality, workload effects, staff attrition, a pricing change, process drift), then injected 23 types of data-quality defects.
2. **Python data cleaning.** I wrote reusable validation and cleaning modules that log every decision. Each injected defect was detected with the exact count (verified by automated tests). The quality score went from 99.13 to 99.98 without silently deleting data.
3. **Exploratory analysis.** Seven executed notebooks and 50 publication-quality charts cover customers, demand, response and resolution, satisfaction, agents, operations and cost.
4. **PostgreSQL analysis.** A normalised schema whose constraints encode the business rules, 46 analytical queries (CTEs, window functions, MoM/YoY, running totals, segmentation, backlog reconstruction), 8 data-quality checks and 11 reporting views, all executed and documented with real results.
5. **KPI development.** 30 KPIs with explicit numerators, denominators and treatment of cancelled, pending, reopened and open tickets. SQL results are tested to match Python exactly.
6. **Power BI design.** A star schema (5 facts, 8 dimensions, no ambiguous or many-to-many relationships), 71 documented DAX measures, Power Query scripts, a corporate theme, six page layouts, and an interactive HTML prototype of the report built from the real data.
7. **Business insights.** Statistical testing (chi-square, Mann-Whitney, regression, confidence intervals), driver analysis, cost decomposition and a leakage-safe SLA-breach model produced 25 insights, each with evidence, a hypothesis, an action and a KPI to monitor.
8. **Recommendations.** A prioritised 90-day action plan, plus an 8-page Streamlit app so managers can explore the data themselves.

## Key Deliverables

- Reproducible pipeline: `python run_pipeline.py` rebuilds everything
- Data-quality report with a full issue log and before/after scores
- 30-KPI definition document, consistent across Python, SQL and DAX
- PostgreSQL schema, loader, 46 queries, 11 views and auto-generated SQL documentation
- Power BI model documentation, 71 DAX measures, Power Query M, theme, page design, implementation and validation guide
- Interactive 6-page Power BI design prototype (HTML, real data)
- 8-page Streamlit analytics app with filters and CSV downloads
- 7 executed Jupyter notebooks and 50 charts
- Executive summary, support report, operations report, 25 insights, recommendations
- 100 automated tests (pytest)

## What the Analysis Revealed (on the synthetic dataset)

- Email and Web Portal tickets wait about 10-13 hours for a first reply vs minutes on phone and chat, and their SLA compliance is 20-27 points lower.
- Customer satisfaction drops steadily with response time: from 4.14 to 2.95 out of 5.
- Billing SLA compliance fell from 83% to 60% in a year as demand rose 45% and two experienced agents left.
- Critical tickets had the lowest SLA compliance of any priority (55%).
- A creation-time risk score separated tickets that breached 75% of the time from those that breached under 1% of the time.

## Business Value

This type of solution helps a business:

- **Resolve issues faster.** It shows exactly which channels, categories and priorities miss targets and flags at-risk tickets early.
- **Improve customer experience.** It ties satisfaction to measurable service drivers (response time, SLA, first-contact resolution).
- **Raise service quality.** Reopen, escalation and FCR are tracked by team, agent and category.
- **Allocate resources better.** Workload, seasonality and backlog views support staffing decisions.
- **Reduce operational inefficiency.** Process-level failure, processing-time and unit-cost trends point to bottlenecks.
- **Make better-informed decisions.** One trusted set of KPI definitions across every tool.

*No financial savings are claimed. The project establishes measurable baselines and the KPIs needed to quantify the impact of each recommended action.*

## How I Can Help Your Business

I can deliver the same approach on your data: help-desk exports (Zendesk, Freshdesk, Jira Service Management, Salesforce), survey tools and operational databases, delivered as a Power BI report, a SQL reporting layer, a Python pipeline or a Streamlit app.

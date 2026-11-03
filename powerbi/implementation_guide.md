# Power BI Implementation Guide

Step-by-step instructions to assemble and validate the report in **Power BI Desktop** (Windows, current version) using the assets in this folder. Estimated time: 2-3 hours.

> This repository does not contain a `.pbix` because it was produced in a Linux environment without Power BI Desktop. Everything the report needs (tables, M queries, DAX, theme, layout spec, expected values) is generated and validated here.

## 0. Prerequisites

```bash
pip install -r requirements.txt
python run_pipeline.py            # generates data/processed/powerbi/*.csv and all assets
```

## 1. Create the data-folder parameter

1. Home → Transform data → **Manage Parameters → New**.
2. Name `DataFolder`, Type **Text**, Current value: absolute path to `data/processed/powerbi/` **with trailing backslash**, e.g. `C:\Projects\business-operations-customer-support-analytics\data\processed\powerbi\`.

## 2. Load the 13 tables

For each file in `powerbi/power_query/` (except `00_DataFolder_parameter.m`):

1. New Source → **Blank Query** → Advanced Editor → paste the file contents → Done.
2. Rename the query to the file name (e.g. `FactSupportTickets`).
3. Close & Apply.

Create a measures table: Home → Enter data → one empty column → name the table `_Measures`.

## 3. Model view

1. Select `DimDate` → Table tools → **Mark as date table** → `Date`.
2. Create relationships exactly as listed in [`data_model.md`](data_model.md#relationships). Set the `resolved_date_only` relationship to **inactive**.
3. Confirm every relationship is *:1, single direction. Delete any auto-detected relationship not in the list (especially DimAgent ↔ DimDepartment).
4. Sort-by-column: `DimPriority[ticket_priority]` by `priority_sort`; `DimDate[month_name]` by `month`.
5. Hide technical columns from report view (keys, flags) to keep the field list clean.

## 4. Add the DAX measures

1. Open **DAX query view** → New query → paste `powerbi/dax_measures.dax`.
2. Click **Update model with changes** (adds all measures to `_Measures`).
3. Run the query: the `EVALUATE` result returns the headline KPIs.
4. Set formats: rates → Percentage (1 dp); hours → Decimal (1 dp); costs → Currency.
5. Create the `FRT Band` calculated column from `dashboard_design.md` (page 3).

## 5. Validate before building visuals

Compare the EVALUATE output (no filters) with `powerbi/validation/expected_kpi_values.csv`:

| Measure | Expected |
|---|---|
| Total Tickets | 24,000 |
| Open Tickets | 257 |
| SLA Compliance Rate | 0.7291 |
| First Contact Resolution Rate | 0.2149 |
| Avg Resolution Time (h) | 34.46 |
| Avg Customer Satisfaction | 3.750 |
| Operational Success Rate | 0.9800 |
| Cost per Resolved Ticket | 479.98 |

All values must match to the shown precision. If they do not: check that flags loaded as whole numbers, that `sla_met` blanks were not converted to 0, and that no extra relationship exists. (These expected values are also produced independently by SQL view `support.v_kpi_summary`.)

Additional filter checks (use a table visual with the measure and the slicer value):

| Filter | Measure | Expected (from Python/SQL) |
|---|---|---|
| DimDepartment = Returns & Refunds | SLA Compliance Rate | 0.5000 |
| DimSupportChannel = Phone | Avg First Response Time (h) | ≈ 0.08 |
| Year = 2025, Billing & Accounts | SLA Compliance Rate | 0.6008 |

## 6. Apply the theme and build the pages

1. View → Themes → **Browse for themes** → `powerbi/theme/support_analytics_theme.json`.
2. Canvas 1280×720; page background is set by the theme.
3. Build the six pages, tooltip page and drill-through pages following [`dashboard_design.md`](dashboard_design.md). The HTML prototype (`powerbi/dashboard_prototype/index.html`) shows the intended look of each page with real numbers; open it in a browser alongside Power BI.
4. Add page-navigator buttons and sync the Date and Department slicers (View → Sync slicers).

## 7. Final QA checklist

- [ ] All KPI cards match the expected values with no filters
- [ ] Changing the Date slicer changes every page consistently
- [ ] No visual shows "(Blank)" categories except the 15 unknown-agent tickets on agent visuals
- [ ] Drill-through from any agent / department works
- [ ] Performance analyzer: every visual < 500 ms
- [ ] Accessibility checklist in `dashboard_design.md` complete
- [ ] Save as `powerbi/Business_Operations_Support_Analytics.pbix` and take screenshots into `screenshots/`

## Refreshing with new data

Rerun `python run_pipeline.py`, then Home → Refresh in Power BI. Because the M queries use the `DataFolder` parameter, no query edits are required.

# Project Progress

Status as of the initial build session. All phases in [`docs/implementation_plan.md`](docs/implementation_plan.md) are implemented, executed and tested. Remaining items are those that need tools unavailable in the build environment (Power BI Desktop) or the author's details.

## Phase status

| # | Phase | Status | Evidence |
|---|---|---|---|
| 1 | Project setup | ✅ Done | structure, `requirements.txt`, `.env.example`, `src/config.py`, plan |
| 2 | Data generation | ✅ Done | `src/data_generation/`, `data/raw/` (9 CSVs + manifest), 24,000 tickets / 3,200 customers / 2023-2025 |
| 3 | Data cleaning | ✅ Done | `src/data_cleaning/`, `src/data_validation/`, `data/processed/`, `data/reports/data_quality_report.md` |
| 4 | EDA | ✅ Done | 7 executed notebooks, 50 charts in `visualizations/` |
| 5 | KPI engine | ✅ Done | `src/kpi/kpis.py`, `docs/KPI_definitions.md`, `data/reports/kpi_summary.json` |
| 6 | SQL / PostgreSQL | ✅ Done (executed on PostgreSQL 16.15) | `sql/`, 46 analytical queries + 8 DQ checks + 11 views, `docs/SQL_documentation.md`, `data/reports/sql_results/` |
| 7 | Power BI | ✅ Assets done · ⏳ PBIX pending | star schema CSVs, 13 M queries, 71 DAX measures, theme, model/design/implementation docs, validation values, HTML prototype |
| 8 | Streamlit | ✅ Done | `streamlit_app/` 8 pages + home; AppTest per page; screenshots |
| 9 | Advanced analytics | ✅ Done | stats, RCA, predictive model, 25 insights |
| 10 | Testing | ✅ 100 passed | `python -m pytest` |
| 11 | Documentation | ✅ Done | README, reports/, docs/, upwork_portfolio.md |
| 12 | Final review | ✅ Done | full rebuild from scratch + test run (see below) |

## Verification performed

- `python run_pipeline.py --with-db --notebooks` rebuilt every output from an empty `data/` folder.
- `python -m pytest` → **100 passed** (including SQL tests against a live PostgreSQL 16 instance).
- All 9 raw tables loaded into PostgreSQL with zero constraint violations; all 54 SQL queries executed.
- SQL `v_kpi_summary` = Python KPI engine (asserted in `tests/test_sql.py`).
- Every injected data defect detected with the exact injected count (`tests/test_cleaning.py`, notebook 02).
- Streamlit: every page runs without exceptions (AppTest) and was rendered in a browser for screenshots.
- HTML prototype rendered in Chromium on all six pages, filtered and unfiltered, with no console errors.

## Outstanding tasks

1. **Build the `.pbix`** in Power BI Desktop by following `powerbi/implementation_guide.md`; validate against `powerbi/validation/expected_kpi_values.csv`; save as `powerbi/Business_Operations_Support_Analytics.pbix`.
2. **Add Power BI screenshots** to `screenshots/` (names: `powerbi_page1_executive.png` … `powerbi_page6_sla.png`) and reference them in the README *Screenshots* section.
3. **Fill in author details** in `README.md` (Author section) and the Upwork profile links.
4. Optional: deploy the Streamlit app (Streamlit Community Cloud) and add the link to the README.
5. Optional: push to GitHub and add a CI workflow running `pytest` (SQL tests auto-skip without a database).

## Exact next steps for a future session

```bash
pip install -r requirements.txt
python -m pytest                 # confirm the baseline (100 passed; SQL tests skip without PostgreSQL)
# then work through "Outstanding tasks" above; nothing needs regenerating.
```

Do not rebuild completed phases: `data/`, `visualizations/`, `notebooks/`, `reports/` and `docs/SQL_documentation.md` are already generated and consistent. Rerun `python run_pipeline.py` only if source code changes.

# Implementation Plan

This plan describes how the project is built, in what order, and how each phase is verified.
Progress against it is tracked in [`PROJECT_PROGRESS.md`](../PROJECT_PROGRESS.md).

## Architecture

```
 Faker / NumPy generator ──► data/raw/*.csv  (deliberately imperfect)
                                  │
            src/data_cleaning + src/data_validation
                                  │
                                  ├─► data/reports/  (quality report, issue log)
                                  ▼
                        data/processed/*.csv  (clean + engineered features)
                 ┌────────────────┼──────────────────┬────────────────────┐
                 ▼                ▼                  ▼                    ▼
        src/kpi (KPI engine)  PostgreSQL 16      Power BI star schema   Streamlit app
                 │           (schema, views,     (DAX, Power Query M,  (8 pages,
                 │            45+ queries)        model docs, design)   Plotly)
                 ▼
  EDA notebooks / charts ─► advanced analytics (stats, RCA, ML) ─► reports & insights
```

## Phases

| # | Phase | Main outputs | Verification |
|---|-------|--------------|--------------|
| 1 | Setup | folder structure, `requirements.txt`, config, plan | structure inspected |
| 2 | Data generation | 9 raw CSVs, ≥20k tickets, ≥3k customers, 3 years | generator run + integrity checks |
| 3 | Data cleaning | reusable modules, processed CSVs, quality report | issue log reconciles raw→processed counts |
| 4 | EDA | 7 executed notebooks, charts in `visualizations/` | notebooks executed end-to-end |
| 5 | KPI engine | `src/kpi/kpis.py`, `docs/KPI_definitions.md` | unit tests on hand-built fixtures |
| 6 | SQL | schema, loader, 45+ queries, views | every script executed on PostgreSQL 16; results captured |
| 7 | Power BI | star-schema tables, DAX (40+), M scripts, model + design docs, HTML prototype | DAX logic cross-checked against Python KPIs |
| 8 | Streamlit | multipage app with filters, KPI cards, downloads | `streamlit.testing` AppTest per page + screenshots |
| 9 | Advanced analytics | statistical tests, RCA, SLA-breach model, 20+ insights | numbers generated from data, not hand-typed |
| 10 | Testing | pytest suite | full suite green |
| 11 | Documentation | README, reports, Upwork case study | links and commands checked |
| 12 | Final review | checklist in `PROJECT_PROGRESS.md` | rerun pipeline from scratch |

## Design principles

* **Raw data is immutable.** Cleaning reads `data/raw`, writes `data/processed`; every change is logged.
* **One definition per KPI.** Python, SQL and DAX implement the same documented formula with the same denominators.
* **No fabricated outputs.** Insights, SQL documentation and reports are produced from executed code.
* **Reproducible.** A fixed seed (`DATA_SEED`) regenerates identical data; `python run_pipeline.py` rebuilds everything.

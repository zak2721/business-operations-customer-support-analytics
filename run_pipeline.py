"""Rebuild the entire project from scratch.

    python run_pipeline.py                 # data -> cleaning -> analytics -> charts -> reports -> Power BI assets
    python run_pipeline.py --with-db       # also load PostgreSQL and run all SQL (needs PG* env vars)
    python run_pipeline.py --notebooks     # also re-execute the 7 notebooks

Every step is idempotent; raw data is regenerated deterministically from DATA_SEED.
"""
from __future__ import annotations

import argparse
import logging
import subprocess
import sys
import time
import warnings

warnings.filterwarnings("ignore")
log = logging.getLogger("pipeline")


def step(name, fn):
    t0 = time.perf_counter()
    log.info("▶ %s", name)
    fn()
    log.info("  done in %.1fs", time.perf_counter() - t0)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--with-db", action="store_true", help="load PostgreSQL and execute every SQL query")
    ap.add_argument("--notebooks", action="store_true", help="re-execute the analysis notebooks")
    a = ap.parse_args()

    from src.analytics import reports, run_advanced
    from src.data_cleaning import pipeline
    from src.data_generation import generate_data
    from src.documentation import build_data_dictionary
    from src.feature_engineering import star_schema
    from src.kpi import kpis
    from src.powerbi import build_assets, build_prototype
    from src.visualization import generate_charts

    step("1. Generate synthetic raw data", generate_data.main)
    step("2. Clean, validate, engineer features, quality report", pipeline.main)
    step("3. KPI engine", kpis.main)
    step("4. Power BI star schema", star_schema.main)
    step("5. EDA charts", generate_charts.main)
    step("6. Statistics, root cause, predictive model", run_advanced.run)
    step("7. Business insights & reports", reports.write_all)
    step("8. Power BI assets (M, theme, expected values) & prototype", lambda: (build_assets.main(), build_prototype.main()))
    step("9. Data dictionary", build_data_dictionary.main)
    if a.with_db:
        from src.database import load_postgres, run_sql
        step("10. Load PostgreSQL", lambda: load_postgres.load_all(create_schema=True))
        step("11. Execute SQL & document results", run_sql.main)
    if a.notebooks:
        step("12. Execute notebooks", lambda: subprocess.run([sys.executable, "notebooks/build_notebooks.py"], check=True))
    log.info("✔ Pipeline complete. Run tests with: python -m pytest")


if __name__ == "__main__":
    main()

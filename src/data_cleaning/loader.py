"""Data loading utilities for raw and processed datasets."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from src import config

# Date columns per table (parsed on processed load; raw dates are parsed by the
# cleaners because raw data contains mixed formats on purpose).
DATE_COLUMNS: dict[str, list[str]] = {
    "customers": ["registration_date"],
    "agents": ["hire_date"],
    "support_tickets": ["ticket_created_date", "first_response_date", "resolved_date", "created_date"],
    "tickets_enriched": ["ticket_created_date", "first_response_date", "resolved_date", "created_date"],
    "customer_feedback": ["feedback_date"],
    "operations": ["operation_date"],
    "agent_performance": ["performance_date"],
    "business_costs": ["cost_date"],
    "calendar": ["date"],
}


class DataLoadError(RuntimeError):
    """Raised when an expected dataset is missing or unreadable."""


def _read(path: Path, parse_dates: list[str] | None = None) -> pd.DataFrame:
    if not path.exists():
        raise DataLoadError(f"Dataset not found: {path}. Run the pipeline first (python run_pipeline.py).")
    try:
        df = pd.read_csv(path, low_memory=False)
    except Exception as exc:  # pragma: no cover - defensive
        raise DataLoadError(f"Could not read {path}: {exc}") from exc
    for col in parse_dates or []:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def load_raw(name: str, raw_dir: Path = config.RAW_DIR) -> pd.DataFrame:
    """Load one raw CSV as strings/numbers exactly as stored (no date parsing)."""
    return _read(raw_dir / f"{name}.csv")


def load_all_raw(raw_dir: Path = config.RAW_DIR) -> dict[str, pd.DataFrame]:
    return {n: load_raw(n, raw_dir) for n in config.ACTIVE_RAW_FILES}


def load_processed(name: str, processed_dir: Path = config.PROCESSED_DIR) -> pd.DataFrame:
    """Load a processed CSV with its date columns parsed."""
    return _read(processed_dir / f"{name}.csv", DATE_COLUMNS.get(name))


def load_all_processed(processed_dir: Path = config.PROCESSED_DIR) -> dict[str, pd.DataFrame]:
    names = config.ACTIVE_RAW_FILES + ["tickets_enriched"]
    return {n: load_processed(n, processed_dir) for n in names}

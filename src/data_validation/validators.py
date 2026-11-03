"""Reusable, table-agnostic data validation checks.

Each function returns plain pandas objects so results can be logged, tested
and written to the data-quality report.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def profile(df: pd.DataFrame, name: str) -> pd.DataFrame:
    """Column-level structure profile: dtype, nulls, distinct values."""
    return pd.DataFrame({
        "table": name,
        "column": df.columns,
        "dtype": [str(t) for t in df.dtypes],
        "non_null": df.notna().sum().values,
        "missing": df.isna().sum().values,
        "missing_pct": (df.isna().mean().values * 100).round(2),
        "distinct": [df[c].nunique(dropna=True) for c in df.columns],
    })


def missing_summary(df: pd.DataFrame) -> pd.Series:
    """Missing values per column (only columns with at least one missing)."""
    s = df.isna().sum()
    return s[s > 0].sort_values(ascending=False)


def exact_duplicates(df: pd.DataFrame) -> int:
    """Number of rows that are exact copies of an earlier row."""
    return int(df.duplicated().sum())


def key_duplicates(df: pd.DataFrame, key: str) -> int:
    """Number of rows whose key value already appeared earlier."""
    return int(df[key].duplicated().sum())


def is_primary_key(df: pd.DataFrame, key: str) -> bool:
    return bool(df[key].notna().all() and df[key].is_unique)


def orphan_keys(child: pd.DataFrame, fk: str, parent: pd.DataFrame, pk: str) -> pd.Series:
    """Boolean mask of child rows whose non-null FK is absent from the parent."""
    return child[fk].notna() & ~child[fk].isin(parent[pk])


def out_of_range(s: pd.Series, low: float, high: float) -> pd.Series:
    """Mask of non-null values outside [low, high]."""
    return s.notna() & ((s < low) | (s > high))


def chronology_violations(df: pd.DataFrame, earlier: str, later: str) -> pd.Series:
    """Mask where both timestamps exist and `later` precedes `earlier`."""
    return df[earlier].notna() & df[later].notna() & (df[later] < df[earlier])


def robust_zscore(s: pd.Series) -> pd.Series:
    """Median/MAD z-score; robust to the very outliers it is meant to find."""
    med = s.median()
    mad = (s - med).abs().median()
    if mad == 0 or np.isnan(mad):
        return pd.Series(0.0, index=s.index)
    return 0.6745 * (s - med) / mad


def iqr_outliers(s: pd.Series, k: float = 3.0) -> pd.Series:
    """Mask of values beyond Q1 - k*IQR or Q3 + k*IQR."""
    q1, q3 = s.quantile([0.25, 0.75])
    iqr = q3 - q1
    return (s < q1 - k * iqr) | (s > q3 + k * iqr)


def quality_dimensions(df: pd.DataFrame, critical_cols: list[str], key: str | None,
                       invalid_mask: pd.Series | None = None) -> dict:
    """Score completeness, uniqueness and validity (0-100) for one table."""
    cols = [c for c in critical_cols if c in df.columns]
    completeness = float(df[cols].notna().mean().mean() * 100) if cols else 100.0
    if key and key in df.columns:
        uniqueness = float((1 - df.duplicated().mean()) * (1 - df[key].duplicated().mean()) * 100)
    else:
        uniqueness = float((1 - df.duplicated().mean()) * 100)
    validity = float((1 - (invalid_mask.mean() if invalid_mask is not None and len(invalid_mask) else 0)) * 100)
    overall = 0.4 * completeness + 0.3 * uniqueness + 0.3 * validity
    return {"completeness": round(completeness, 2), "uniqueness": round(uniqueness, 2),
            "validity": round(validity, 2), "quality_score": round(overall, 2)}

from __future__ import annotations

import pandas as pd

from excel_analyst.schema_analysis.models import ColumnKind, ColumnProfile, TableProfile

_TOP_K = 5


def _infer_kind(series: pd.Series) -> ColumnKind:
    if pd.api.types.is_datetime64_any_dtype(series.dtype):
        return ColumnKind.DATETIME
    if pd.api.types.is_bool_dtype(series.dtype):
        return ColumnKind.CATEGORICAL
    if pd.api.types.is_numeric_dtype(series.dtype):
        return ColumnKind.NUMERIC

    as_dt = pd.to_datetime(series, errors="coerce", utc=False)
    if as_dt.notna().mean() > 0.85:
        return ColumnKind.DATETIME

    as_num = pd.to_numeric(series, errors="coerce")
    if as_num.notna().mean() > 0.85:
        return ColumnKind.NUMERIC

    nunique = series.nunique(dropna=True)
    if nunique <= min(50, max(10, len(series) // 10 or 1)):
        return ColumnKind.CATEGORICAL
    return ColumnKind.TEXT


def _profile_column(name: str, series: pd.Series) -> ColumnProfile:
    kind = _infer_kind(series)
    null_count = int(series.isna().sum())
    non_null_count = int(series.notna().sum())

    mean = min_v = max_v = None
    unique_count = None
    top_values: list[dict] = []

    if kind == ColumnKind.NUMERIC:
        num = pd.to_numeric(series, errors="coerce")
        mean = float(num.mean()) if non_null_count else None
        min_v = float(num.min()) if non_null_count else None
        max_v = float(num.max()) if non_null_count else None
    elif kind == ColumnKind.DATETIME:
        dt = pd.to_datetime(series, errors="coerce", utc=False)
        if non_null_count:
            min_v = dt.min().isoformat()
            max_v = dt.max().isoformat()
    elif kind in (ColumnKind.CATEGORICAL, ColumnKind.TEXT):
        vc = series.astype("string").value_counts(dropna=True).head(_TOP_K)
        unique_count = int(series.nunique(dropna=True))
        top_values = [{"value": str(i), "count": int(c)} for i, c in vc.items()]

    return ColumnProfile(
        name=name,
        kind=kind,
        dtype=str(series.dtype),
        null_count=null_count,
        non_null_count=non_null_count,
        mean=mean,
        min=min_v,
        max=max_v,
        unique_count=unique_count,
        top_values=top_values,
    )


def analyze_table(df: pd.DataFrame, table_name: str) -> TableProfile:
    columns = [_profile_column(str(c), df[c]) for c in df.columns]
    return TableProfile(table_name=table_name, row_count=int(len(df)), columns=columns)

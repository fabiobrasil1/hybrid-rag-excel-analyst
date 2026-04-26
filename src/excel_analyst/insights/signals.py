from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from excel_analyst.schema_analysis.models import ColumnKind, TableProfile


def _numeric_columns(profile: TableProfile) -> list[str]:
    return [c.name for c in profile.columns if c.kind == ColumnKind.NUMERIC]


def _datetime_columns(profile: TableProfile) -> list[str]:
    return [c.name for c in profile.columns if c.kind == ColumnKind.DATETIME]


def compute_insight_signals(df: pd.DataFrame, profile: TableProfile) -> dict[str, Any]:
    signals: dict[str, Any] = {
        "table": profile.table_name,
        "row_count": int(len(df)),
        "numeric_highlights": [],
        "concentration": [],
        "outliers_iqr": [],
        "simple_trend": None,
    }

    for col in _numeric_columns(profile):
        series = pd.to_numeric(df[col], errors="coerce")
        clean = series.dropna()
        if clean.empty:
            continue
        arr = clean.to_numpy(dtype=float)
        max_idx = int(np.nanargmax(arr))
        min_idx = int(np.nanargmin(arr))
        signals["numeric_highlights"].append(
            {
                "column": col,
                "max": float(arr[max_idx]),
                "min": float(arr[min_idx]),
                "mean": float(np.nanmean(arr)),
            }
        )

        positive = arr[arr > 0]
        if positive.size:
            total = float(positive.sum())
            if total > 0:
                top = np.sort(positive)[-min(3, positive.size) :]
                share = float(top.sum() / total)
                signals["concentration"].append(
                    {
                        "column": col,
                        "top3_share_of_positive_sum": share,
                        "note": "Soma dos 3 maiores valores positivos dividida pela soma de todos os positivos.",
                    }
                )

        q1, q3 = np.percentile(arr, [25, 75])
        iqr = q3 - q1
        if iqr > 0:
            low, high = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            mask = (arr < low) | (arr > high)
            count = int(mask.sum())
            if count:
                example_values = arr[mask][:5].tolist()
                signals["outliers_iqr"].append(
                    {
                        "column": col,
                        "count": count,
                        "example_values": [float(x) for x in example_values],
                    }
                )

    dt_cols = _datetime_columns(profile)
    num_cols = _numeric_columns(profile)
    if dt_cols and num_cols:
        dt = dt_cols[0]
        num = num_cols[0]
        tmp = df[[dt, num]].copy()
        tmp[dt] = pd.to_datetime(tmp[dt], errors="coerce")
        tmp[num] = pd.to_numeric(tmp[num], errors="coerce")
        tmp = tmp.dropna().sort_values(dt)
        if len(tmp) >= 3:
            y = tmp[num].to_numpy(dtype=float)
            x = np.arange(len(y), dtype=float)
            slope, intercept = np.polyfit(x, y, 1)
            signals["simple_trend"] = {
                "datetime_column": dt,
                "value_column": num,
                "points_used": int(len(tmp)),
                "ols_slope_per_step": float(slope),
                "ols_intercept": float(intercept),
                "note": "Tendência linear simples ao longo da ordem temporal (MVP).",
            }
    elif not dt_cols:
        signals["simple_trend"] = {
            "skipped": True,
            "reason": "Nenhuma coluna datetime inferida para correlacionar com métricas.",
        }

    return signals

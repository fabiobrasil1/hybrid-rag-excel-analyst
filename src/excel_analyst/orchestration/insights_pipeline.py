from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from excel_analyst.insights.signals import compute_insight_signals
from excel_analyst.llm.plan_llm import explain_insights_from_signals
from excel_analyst.schema_analysis.models import TableProfile


@dataclass
class InsightsPipelineResult:
    signals: dict[str, Any]
    narrative: str
    errors: list[str] = field(default_factory=list)


def run_insights_pipeline(
    question: str | None,
    df: pd.DataFrame,
    profile: TableProfile,
) -> InsightsPipelineResult:
    errors: list[str] = []
    try:
        signals = compute_insight_signals(df, profile)
    except Exception as e:
        return InsightsPipelineResult(signals={}, narrative="", errors=[f"Sinais: {e}"])
    try:
        narrative = explain_insights_from_signals(question, signals)
    except Exception as e:
        errors.append(f"Narrativa: {e}")
        narrative = "Sinais calculados; falha ao gerar narrativa."
    return InsightsPipelineResult(signals=signals, narrative=narrative, errors=errors)

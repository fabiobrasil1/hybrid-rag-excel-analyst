from __future__ import annotations

from enum import Enum


class QuestionKind(str, Enum):
    CALCULATION = "calculation"
    COMPARISON = "comparison"
    INSIGHT = "insight"
    LOOKUP = "lookup"
    GENERAL = "general"


def classify_intent(question: str) -> QuestionKind:
    q = question.lower()
    if any(k in q for k in ("insight", "insights", "padrão", "padrao", "outlier", "tendência", "tendencia")):
        return QuestionKind.INSIGHT
    if any(k in q for k in ("compar", "versus", " vs ", " maior ", " menor ")):
        return QuestionKind.COMPARISON
    if any(
        k in q
        for k in (
            "média",
            "media",
            "soma",
            "total",
            "contar",
            "quantos",
            "quantas",
            "máximo",
            "maximo",
            "mínimo",
            "minimo",
            "agrup",
            "group",
            "top ",
            "rank",
        )
    ):
        return QuestionKind.CALCULATION
    if any(k in q for k in ("liste", "mostre", "filtr", "onde ", "quais linhas")):
        return QuestionKind.LOOKUP
    return QuestionKind.GENERAL


def intent_pt_label(kind: QuestionKind) -> str:
    return {
        QuestionKind.CALCULATION: "cálculo / agregação",
        QuestionKind.COMPARISON: "comparação",
        QuestionKind.INSIGHT: "insights",
        QuestionKind.LOOKUP: "consulta / filtro",
        QuestionKind.GENERAL: "geral",
    }[kind]

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from excel_analyst.execution import dataframe_to_rows_json, run_plan
from excel_analyst.execution.errors import ExecutionError
from excel_analyst.execution.plan import ExecutionPlan
from excel_analyst.llm.plan_llm import explain_execution_answer, propose_execution_plan
from excel_analyst.orchestration.intent import QuestionKind, classify_intent, intent_pt_label
from excel_analyst.retrieval.metadata_rag import MetadataRAG
from excel_analyst.schema_analysis.models import TableProfile


@dataclass
class PipelineResult:
    intent: QuestionKind
    intent_label: str
    rag_documents: list[str]
    rag_metadatas: list[dict]
    plan: ExecutionPlan | None
    result: dict[str, Any] | None
    answer_text: str
    errors: list[str] = field(default_factory=list)


def _catalog_for_table(profile: TableProfile) -> list[dict[str, Any]]:
    return [
        {
            "name": c.name,
            "kind": c.kind.value,
            "dtype": c.dtype,
            "non_null_count": c.non_null_count,
            "null_count": c.null_count,
        }
        for c in profile.columns
    ]


def run_question_pipeline(
    question: str,
    tables: dict[str, pd.DataFrame],
    active_table: str,
    profile: TableProfile,
    rag: MetadataRAG | None,
) -> PipelineResult:
    errors: list[str] = []
    intent = classify_intent(question)
    intent_label = intent_pt_label(intent)

    rag_docs: list[str] = []
    rag_meta: list[dict] = []
    if rag is not None:
        try:
            rag_docs, rag_meta = rag.search(question, top_k=8)
        except Exception as e:
            errors.append(f"RAG: falha na busca ({e})")

    plan: ExecutionPlan | None = None
    result_payload: dict[str, Any] | None = None
    answer_text = ""

    try:
        plan = propose_execution_plan(
            question=question,
            target_table=active_table,
            column_catalog=_catalog_for_table(profile),
            rag_chunks=rag_docs,
        )
    except Exception as e:
        errors.append(f"Plano: {e}")
        return PipelineResult(
            intent=intent,
            intent_label=intent_label,
            rag_documents=rag_docs,
            rag_metadatas=rag_meta,
            plan=None,
            result=None,
            answer_text="",
            errors=errors,
        )

    try:
        df = run_plan(tables, plan)
        result_payload = dataframe_to_rows_json(df)
    except ExecutionError as e:
        errors.append(f"Execução: {e}")
    except Exception as e:
        errors.append(f"Execução: {e}")

    if result_payload is not None:
        try:
            answer_text = explain_execution_answer(question, result_payload, intent_label)
        except Exception as e:
            errors.append(f"Resposta (LLM): {e}")
            answer_text = "Execução concluída; falha ao gerar texto explicativo."

    return PipelineResult(
        intent=intent,
        intent_label=intent_label,
        rag_documents=rag_docs,
        rag_metadatas=rag_meta,
        plan=plan,
        result=result_payload,
        answer_text=answer_text,
        errors=errors,
    )

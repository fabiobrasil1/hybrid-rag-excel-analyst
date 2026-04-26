from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from excel_analyst.execution.plan import ExecutionPlan
from excel_analyst.llm.settings import LLMSettings


def _build_messages(
    question: str,
    target_table: str,
    column_catalog: list[dict[str, Any]],
    rag_chunks: list[str],
) -> list[dict[str, str]]:
    allow = json.dumps(column_catalog, ensure_ascii=False)
    rag_text = "\n---\n".join(rag_chunks) if rag_chunks else "(sem contexto recuperado)"
    system = (
        "Você gera apenas JSON válido para um ExecutionPlan de analytics. "
        "Não calcule resultados finais da pergunta do usuário. "
        "Use somente nomes de colunas presentes no catálogo. "
        f"A tabela alvo deve ser exatamente: {target_table!r}. "
        "Responda com um único objeto JSON (sem markdown)."
    )
    user = (
        f"Pergunta:\n{question}\n\n"
        f"Catálogo de colunas (allowlist):\n{allow}\n\n"
        f"Contexto RAG (metadados):\n{rag_text}\n\n"
        "Monte um ExecutionPlan adequado. "
        "Operadores de filtro permitidos: eq, ne, gt, lt, ge, le, contains. "
        "Funções de agregação: mean, sum, count, min, max. "
        "Se a pergunta pedir 'top N', use order_by + limit. "
        "Se não houver agregação, deixe aggregations vazio e use filters/order_by/limit sobre linhas."
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def propose_execution_plan(
    question: str,
    target_table: str,
    column_catalog: list[dict[str, Any]],
    rag_chunks: list[str],
) -> ExecutionPlan:
    settings = LLMSettings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY não configurada; não é possível gerar plano via LLM.")
    client = OpenAI(api_key=settings.openai_api_key)
    messages = _build_messages(question, target_table, column_catalog, rag_chunks)
    schema = json.dumps(ExecutionPlan.model_json_schema(), ensure_ascii=False)
    messages[0]["content"] += f"\n\nJSON Schema esperado:\n{schema}"
    completion = client.chat.completions.create(
        model=settings.openai_model,
        temperature=0,
        response_format={"type": "json_object"},
        messages=messages,
    )
    content = completion.choices[0].message.content or "{}"
    data = json.loads(content)
    plan = ExecutionPlan.model_validate(data)
    if plan.target_table != target_table:
        raise ValueError("O LLM alterou a tabela alvo; plano rejeitado por segurança.")
    return plan


def explain_execution_answer(
    question: str,
    result_payload: dict[str, Any],
    intent_label: str,
) -> str:
    settings = LLMSettings()
    if not settings.openai_api_key:
        return (
            "Resultado numérico calculado pelo engine (abaixo). "
            "Configure OPENAI_API_KEY para obter explicação em linguagem natural."
        )
    client = OpenAI(api_key=settings.openai_api_key)
    payload = json.dumps(result_payload, ensure_ascii=False)
    system = (
        "Você explica resultados analíticos em português. "
        "Use APENAS números e categorias presentes no JSON de resultados. "
        "Não invente valores, não extrapole totais fora do JSON. "
        "Se o JSON estiver vazio ou houver truncamento, diga isso explicitamente."
    )
    user = (
        f"Intenção classificada: {intent_label}\n"
        f"Pergunta original:\n{question}\n\n"
        f"Dados tabulares (fonte da verdade):\n{payload}\n"
    )
    completion = client.chat.completions.create(
        model=settings.openai_model,
        temperature=0.2,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
    )
    return (completion.choices[0].message.content or "").strip()


def explain_insights_from_signals(question: str | None, signals: dict[str, Any]) -> str:
    settings = LLMSettings()
    if not settings.openai_api_key:
        return "Sinais estatísticos calculados (JSON abaixo). Configure OPENAI_API_KEY para narração."
    client = OpenAI(api_key=settings.openai_api_key)
    payload = json.dumps(signals, ensure_ascii=False)
    system = (
        "Você interpreta sinais estatísticos já calculados. "
        "Não crie novas métricas; cite apenas o que consta no JSON."
    )
    q = question or "Visão geral dos dados"
    user = f"Pergunta/contexto:\n{q}\n\nSinais:\n{payload}\n"
    completion = client.chat.completions.create(
        model=settings.openai_model,
        temperature=0.2,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
    )
    return (completion.choices[0].message.content or "").strip()

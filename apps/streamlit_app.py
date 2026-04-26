from __future__ import annotations

import json
import sys
import tempfile
import uuid
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from excel_analyst.ingest import IngestError, load_uploaded_tables
from excel_analyst.orchestration import (
    run_insights_pipeline,
    run_question_pipeline,
)
from excel_analyst.retrieval import MetadataRAG
from excel_analyst.schema_analysis import analyze_table

st.set_page_config(page_title="Hybrid RAG Excel Analyst", layout="wide")
st.title("Hybrid RAG Excel Analyst")
st.caption(
    "Cálculos via DuckDB/pandas · RAG só sobre metadados · LLM para plano e texto (sem inventar números fora do resultado)."
)


def _reset_session_upload() -> None:
    for k in ("dfs", "profiles", "rag", "dataset_id", "tmp_path"):
        st.session_state.pop(k, None)


def _persist_upload(uploaded) -> Path:
    suffix = Path(uploaded.name).suffix.lower()
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(uploaded.getbuffer())
    tmp.flush()
    tmp.close()
    return Path(tmp.name)


uploaded = st.file_uploader("Envie um CSV ou Excel (.xlsx)", type=["csv", "xlsx"])
if uploaded is not None:
    if st.session_state.get("upload_name") != uploaded.name:
        _reset_session_upload()
        st.session_state["upload_name"] = uploaded.name
    if "dfs" not in st.session_state:
        try:
            path = _persist_upload(uploaded)
            st.session_state["tmp_path"] = str(path)
            dfs = load_uploaded_tables(path)
            profiles = {name: analyze_table(df, name) for name, df in dfs.items()}
            dataset_id = str(uuid.uuid4())
            chroma_dir = ROOT / "storage" / f"chroma_{dataset_id}"
            chroma_dir.mkdir(parents=True, exist_ok=True)
            rag = MetadataRAG(persist_directory=str(chroma_dir))
            rag.index_profiles(dataset_id, list(profiles.values()))
            st.session_state["dfs"] = dfs
            st.session_state["profiles"] = profiles
            st.session_state["rag"] = rag
            st.session_state["dataset_id"] = dataset_id
        except IngestError as e:
            st.error(str(e))
            st.stop()

if "dfs" not in st.session_state:
    st.info("Faça upload de um arquivo para começar.")
    st.stop()

dfs: dict[str, pd.DataFrame] = st.session_state["dfs"]
profiles: dict = st.session_state["profiles"]
rag: MetadataRAG = st.session_state["rag"]

table_names = list(dfs.keys())
active = st.selectbox("Aba / tabela ativa", table_names, index=0)
df_active = dfs[active]
profile_active = profiles[active]

left, right = st.columns(2)
with left:
    st.subheader("Preview")
    st.dataframe(df_active.head(25), width="stretch")
with right:
    st.subheader("Schema inferido")
    st.json(profile_active.model_dump(), expanded=False)

st.divider()
q1, q2 = st.columns(2)
with q1:
    st.subheader("Pergunta (NL)")
    question = st.text_area("Sua pergunta", height=120, placeholder="Ex.: Qual a média de vendas por região?")
    ask = st.button("Executar pipeline (RAG + plano + engine)", type="primary")
with q2:
    st.subheader("Insights automáticos")
    insight_q = st.text_input("Contexto opcional para a narrativa", placeholder="Ex.: foco em outliers de receita")
    insights_btn = st.button("Calcular sinais + narrativa")

if ask:
    if not question.strip():
        st.warning("Digite uma pergunta.")
    else:
        with st.spinner("Interpretando, recuperando contexto, executando…"):
            result = run_question_pipeline(
                question=question.strip(),
                tables=dfs,
                active_table=active,
                profile=profile_active,
                rag=rag,
            )
        st.markdown(f"**Intenção (heurística):** `{result.intent.value}` — {result.intent_label}")
        if result.errors:
            for err in result.errors:
                st.error(err)
        with st.expander("Contexto RAG (trechos)", expanded=False):
            for doc in result.rag_documents:
                st.markdown(doc)
        if result.plan:
            with st.expander("Plano de execução (JSON)", expanded=False):
                st.json(json.loads(result.plan.model_dump_json()), expanded=True)
        if result.result:
            st.subheader("Resultado numérico (engine)")
            res = result.result
            out_df = pd.DataFrame(res["rows"], columns=res["columns"])
            st.dataframe(out_df, width="stretch")
            if res.get("truncated"):
                st.caption(f"Pré-visualização truncada; total de linhas: {res.get('row_count')}")
        st.subheader("Resposta (texto)")
        st.markdown(result.answer_text or "_Sem texto gerado._")

if insights_btn:
    with st.spinner("Calculando sinais estatísticos…"):
        ins = run_insights_pipeline(insight_q or None, df_active, profile_active)
    if ins.errors:
        for err in ins.errors:
            st.warning(err)
    st.subheader("Sinais (JSON)")
    st.json(ins.signals, expanded=True)
    st.subheader("Narrativa")
    st.markdown(ins.narrative)

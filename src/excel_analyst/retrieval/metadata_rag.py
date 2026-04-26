from __future__ import annotations

import uuid

import chromadb
from chromadb.utils import embedding_functions

from excel_analyst.schema_analysis.models import ColumnKind, ColumnProfile, TableProfile


def _column_document(table_name: str, col: ColumnProfile) -> str:
    lines = [
        f"Tabela: {table_name}",
        f"Coluna: {col.name}",
        f"Tipo lógico: {col.kind.value}",
        f"dtype (pandas): {col.dtype}",
        f"Linhas não nulas: {col.non_null_count}; nulos: {col.null_count}",
    ]
    if col.kind == ColumnKind.NUMERIC and col.mean is not None:
        lines.append(
            f"Estatísticas descritivas (coluna inteira): média={col.mean}, min={col.min}, max={col.max}"
        )
    if col.kind == ColumnKind.DATETIME:
        lines.append(f"Intervalo de datas (coluna inteira): min={col.min}, max={col.max}")
    if col.top_values:
        top = ", ".join(f"{t['value']}({t['count']})" for t in col.top_values[:5])
        lines.append(f"Valores frequentes (amostra): {top}")
    if col.unique_count is not None:
        lines.append(f"Cardinalidade aproximada: {col.unique_count}")
    return "\n".join(lines)


class MetadataRAG:
    """RAG leve apenas sobre metadados de schema (sem valores de células individuais)."""

    def __init__(self, persist_directory: str | None = None) -> None:
        self._ef = embedding_functions.DefaultEmbeddingFunction()
        self._client = chromadb.PersistentClient(path=persist_directory or ".chroma_data")
        self._collection = None

    def index_profiles(self, dataset_id: str, profiles: list[TableProfile]) -> None:
        name = f"m_{uuid.uuid4().hex[:24]}"
        self._collection = self._client.create_collection(
            name=name,
            embedding_function=self._ef,
            metadata={"dataset_id": dataset_id},
        )
        ids: list[str] = []
        documents: list[str] = []
        metadatas: list[dict] = []
        for profile in profiles:
            for col in profile.columns:
                ids.append(f"{profile.table_name}::{col.name}")
                documents.append(_column_document(profile.table_name, col))
                metadatas.append(
                    {
                        "table": profile.table_name,
                        "column": col.name,
                        "kind": col.kind.value,
                    }
                )
        if documents:
            self._collection.add(ids=ids, documents=documents, metadatas=metadatas)

    def search(self, query: str, top_k: int = 8) -> tuple[list[str], list[dict]]:
        if self._collection is None:
            return [], []
        res = self._collection.query(query_texts=[query], n_results=top_k)
        docs = (res.get("documents") or [[]])[0] or []
        metas = (res.get("metadatas") or [[]])[0] or []
        return list(docs), list(metas)

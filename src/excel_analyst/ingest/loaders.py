from __future__ import annotations

from pathlib import Path

import pandas as pd

from excel_analyst.ingest.errors import IngestError

_ALLOWED_EXCEL_SUFFIXES = {".xlsx"}


def load_csv(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if not path.is_file():
        raise IngestError(f"Arquivo não encontrado: {path}")
    if path.suffix.lower() != ".csv":
        raise IngestError(f"Extensão inválida para CSV: {path.suffix}")
    try:
        return pd.read_csv(path)
    except UnicodeDecodeError as e:
        raise IngestError(
            "Falha de encoding ao ler CSV; tente salvar o arquivo como UTF-8."
        ) from e
    except Exception as e:
        raise IngestError(f"Não foi possível ler o CSV: {path.name}") from e


def load_excel_sheets(path: str | Path) -> dict[str, pd.DataFrame]:
    path = Path(path)
    if not path.is_file():
        raise IngestError(f"Arquivo não encontrado: {path}")
    if path.suffix.lower() not in _ALLOWED_EXCEL_SUFFIXES:
        raise IngestError(
            f"Extensão Excel não suportada no MVP: {path.suffix} (use .xlsx)"
        )
    try:
        xls = pd.ExcelFile(path, engine="openpyxl")
    except Exception as e:
        raise IngestError(f"Não foi possível abrir o Excel: {path.name}") from e

    sheets: dict[str, pd.DataFrame] = {}
    for sheet_name in xls.sheet_names:
        try:
            df = pd.read_excel(xls, sheet_name=sheet_name)
        except Exception as e:
            raise IngestError(f"Erro ao ler a aba '{sheet_name}'") from e
        if df.shape[1] == 0:
            continue
        sheets[sheet_name] = df
    if not sheets:
        raise IngestError("Nenhuma aba com colunas foi encontrada no arquivo Excel.")
    return sheets


def load_uploaded_tables(path: str | Path) -> dict[str, pd.DataFrame]:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return {"default": load_csv(path)}
    if suffix in _ALLOWED_EXCEL_SUFFIXES:
        return load_excel_sheets(path)
    raise IngestError(f"Formato não suportado: {suffix}")

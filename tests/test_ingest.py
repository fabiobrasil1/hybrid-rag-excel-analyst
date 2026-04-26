from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from excel_analyst.ingest import IngestError, load_csv, load_excel_sheets, load_uploaded_tables


def test_load_csv_happy_path(tmp_path: Path) -> None:
    csv_path = tmp_path / "sales.csv"
    csv_path.write_text("region,revenue\nsul,100\nnorte,150\n", encoding="utf-8")

    df = load_csv(csv_path)

    assert list(df.columns) == ["region", "revenue"]
    assert df.shape == (2, 2)


def test_load_uploaded_tables_with_csv_returns_default_table(tmp_path: Path) -> None:
    csv_path = tmp_path / "data.csv"
    csv_path.write_text("a,b\n1,2\n", encoding="utf-8")

    tables = load_uploaded_tables(csv_path)

    assert list(tables.keys()) == ["default"]
    assert tables["default"].shape == (1, 2)


def test_load_excel_sheets_happy_path(tmp_path: Path) -> None:
    xlsx_path = tmp_path / "sample.xlsx"
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        pd.DataFrame({"region": ["sul"], "revenue": [100]}).to_excel(
            writer, sheet_name="vendas", index=False
        )
        pd.DataFrame({"sku": ["A1"], "qty": [3]}).to_excel(writer, sheet_name="itens", index=False)

    sheets = load_excel_sheets(xlsx_path)

    assert set(sheets.keys()) == {"vendas", "itens"}
    assert list(sheets["vendas"].columns) == ["region", "revenue"]


def test_load_uploaded_tables_rejects_unsupported_extension(tmp_path: Path) -> None:
    bad_path = tmp_path / "notes.txt"
    bad_path.write_text("irrelevant", encoding="utf-8")

    with pytest.raises(IngestError):
        load_uploaded_tables(bad_path)

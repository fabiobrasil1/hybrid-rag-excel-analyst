from __future__ import annotations

import re
from typing import Any

import duckdb
import pandas as pd

from excel_analyst.execution.errors import ExecutionError
from excel_analyst.execution.plan import (
    AggFunction,
    AggregationSpec,
    ExecutionPlan,
    FilterOperator,
    FilterSpec,
)


def sanitize_sql_table(name: str) -> str:
    cleaned = re.sub(r"\W+", "_", name.strip())
    if cleaned and cleaned[0].isdigit():
        cleaned = "t_" + cleaned
    return cleaned or "table"


def quote_ident(name: str) -> str:
    if '"' in name:
        raise ExecutionError(f"Identificador inválido: {name!r}")
    return f'"{name}"'


def _assert_col(name: str, cols: set[str], label: str) -> None:
    if not name or not str(name).strip():
        raise ExecutionError(f"{label} vazio.")
    if '"' in str(name):
        raise ExecutionError(f"{label} não pode conter aspas duplas: {name!r}")
    if name not in cols:
        raise ExecutionError(f"{label} inexistente: {name!r}")


def validate_plan(plan: ExecutionPlan, tables: dict[str, pd.DataFrame]) -> None:
    if plan.target_table not in tables:
        raise ExecutionError(f"Tabela alvo inexistente: {plan.target_table!r}")
    if plan.group_by and not plan.aggregations:
        raise ExecutionError("GROUP BY sem agregações não é suportado neste MVP.")
    df = tables[plan.target_table]
    cols = set(str(c) for c in df.columns)
    for g in plan.group_by:
        _assert_col(g, cols, "Coluna de agrupamento")
    for a in plan.aggregations:
        _assert_col(a.column, cols, "Coluna de agregação")
    for f in plan.filters:
        _assert_col(f.column, cols, "Coluna de filtro")
    if plan.order_by:
        oc, _ = plan.order_by
        _assert_col(oc, cols, "Coluna de ordenação")


def _agg_sql(spec: AggregationSpec) -> str:
    col = quote_ident(spec.column)
    if spec.function == AggFunction.MEAN:
        return f"avg({col}) AS mean_{spec.column}"
    if spec.function == AggFunction.SUM:
        return f"sum({col}) AS sum_{spec.column}"
    if spec.function == AggFunction.COUNT:
        return f"count({col}) AS count_{spec.column}"
    if spec.function == AggFunction.MIN:
        return f"min({col}) AS min_{spec.column}"
    if spec.function == AggFunction.MAX:
        return f"max({col}) AS max_{spec.column}"
    raise ExecutionError(f"Função de agregação desconhecida: {spec.function}")


def _filter_sql(f: FilterSpec, params: list[Any]) -> str:
    col = quote_ident(f.column)
    if f.operator == FilterOperator.CONTAINS:
        params.append(f"%{f.value}%")
        return f"{col} LIKE ?"
    params.append(f.value)
    op_map = {
        FilterOperator.EQ: "=",
        FilterOperator.NE: "!=",
        FilterOperator.GT: ">",
        FilterOperator.LT: "<",
        FilterOperator.GE: ">=",
        FilterOperator.LE: "<=",
    }
    sym = op_map.get(f.operator)
    if sym is None:
        raise ExecutionError(f"Operador de filtro não suportado: {f.operator}")
    return f"{col} {sym} ?"


def build_sql(plan: ExecutionPlan, sql_table: str) -> tuple[str, list[Any]]:
    params: list[Any] = []
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", sql_table):
        raise ExecutionError("Nome interno de tabela inválido após sanitização.")
    from_clause = sql_table
    where_parts = []
    for f in plan.filters:
        where_parts.append(_filter_sql(f, params))
    where_sql = (" WHERE " + " AND ".join(where_parts)) if where_parts else ""

    if plan.aggregations:
        select_parts = [*(quote_ident(g) for g in plan.group_by), *(_agg_sql(a) for a in plan.aggregations)]
        select_sql = "SELECT " + ", ".join(select_parts) + f" FROM {from_clause}" + where_sql
        if plan.group_by:
            select_sql += " GROUP BY " + ", ".join(quote_ident(g) for g in plan.group_by)
    else:
        select_sql = "SELECT * FROM " + from_clause + where_sql

    if plan.order_by:
        col, direction = plan.order_by
        select_sql += f" ORDER BY {quote_ident(col)} {direction.upper()}"

    if plan.limit is not None:
        select_sql += f" LIMIT {int(plan.limit)}"

    return select_sql, params


def run_plan(tables: dict[str, pd.DataFrame], plan: ExecutionPlan) -> pd.DataFrame:
    validate_plan(plan, tables)
    sql_table = sanitize_sql_table(plan.target_table)
    con = duckdb.connect(database=":memory:")
    try:
        for logical, df in tables.items():
            con.register(sanitize_sql_table(logical), df)
        sql, params = build_sql(plan, sql_table)
        return con.execute(sql, params).df()
    except ExecutionError:
        raise
    except Exception as e:
        raise ExecutionError("Falha ao executar consulta no DuckDB.") from e
    finally:
        con.close()


def dataframe_to_rows_json(df: pd.DataFrame, max_rows: int = 500) -> dict[str, Any]:
    truncated = len(df) > max_rows
    view = df.head(max_rows)
    rows: list[list[Any]] = view.astype(object).where(pd.notna(view), None).values.tolist()
    return {
        "columns": [str(c) for c in view.columns],
        "rows": rows,
        "row_count": int(len(df)),
        "truncated": truncated,
    }

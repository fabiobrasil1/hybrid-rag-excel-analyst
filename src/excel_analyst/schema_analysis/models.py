from __future__ import annotations

from enum import Enum
from typing import Any, List, Optional, Union

from pydantic import BaseModel, Field


class ColumnKind(str, Enum):
    NUMERIC = "numeric"
    CATEGORICAL = "categorical"
    DATETIME = "datetime"
    TEXT = "text"
    UNKNOWN = "unknown"


class ColumnProfile(BaseModel):
    name: str
    kind: ColumnKind
    dtype: str
    null_count: int
    non_null_count: int
    mean: Optional[float] = None
    min: Optional[Union[float, str]] = None
    max: Optional[Union[float, str]] = None
    unique_count: Optional[int] = None
    top_values: List[dict[str, Any]] = Field(default_factory=list)


class TableProfile(BaseModel):
    table_name: str
    row_count: int
    columns: List[ColumnProfile]

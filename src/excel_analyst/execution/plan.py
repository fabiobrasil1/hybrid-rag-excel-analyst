from __future__ import annotations

from enum import Enum
from typing import Literal, Optional, Tuple, Union

from pydantic import BaseModel, Field


class AggFunction(str, Enum):
    MEAN = "mean"
    SUM = "sum"
    COUNT = "count"
    MIN = "min"
    MAX = "max"


class AggregationSpec(BaseModel):
    column: str
    function: AggFunction


class FilterOperator(str, Enum):
    EQ = "eq"
    NE = "ne"
    GT = "gt"
    LT = "lt"
    GE = "ge"
    LE = "le"
    CONTAINS = "contains"


class FilterSpec(BaseModel):
    column: str
    operator: FilterOperator
    value: Optional[Union[str, float, int, bool]] = None


class ExecutionPlan(BaseModel):
    target_table: str
    aggregations: list[AggregationSpec] = Field(default_factory=list)
    group_by: list[str] = Field(default_factory=list)
    filters: list[FilterSpec] = Field(default_factory=list)
    order_by: Optional[Tuple[str, Literal["asc", "desc"]]] = None
    limit: Optional[int] = Field(default=None, ge=1, le=10_000)

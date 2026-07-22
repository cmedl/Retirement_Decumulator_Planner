"""Optimization objective models."""

from dataclasses import dataclass, field
from enum import StrEnum


class ObjectiveName(StrEnum):
    FLAT_AFTER_TAX_INCOME = "flat_after_tax_income"
    MINIMIZE_TAX_VARIANCE = "minimize_tax_variance"
    MINIMIZE_LIFETIME_TAX = "minimize_lifetime_tax"
    DEPLETE_RRSP_BY_AGE = "deplete_rrsp_by_age"
    RESPECT_OAS_CLAWBACK = "respect_oas_clawback"
    MINIMIZE_SECTION7_OUTFLOW = "minimize_section7_outflow"


@dataclass(slots=True)
class OptimizationObjective:
    """Single optimization objective with rank priority."""

    name: ObjectiveName
    priority: int
    target_value: float | int | None = None
    enabled: bool = True


@dataclass(slots=True)
class ObjectiveSet:
    """Priority-ordered objective container."""

    objectives: list[OptimizationObjective] = field(default_factory=list)

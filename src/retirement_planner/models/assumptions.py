"""Economic assumption models."""

from dataclasses import dataclass


@dataclass(slots=True)
class EconomicAssumptions:
    """Core configurable rates for projections."""

    inflation_rate: float = 0.02
    investment_return_rate: float = 0.05
    salary_growth_rate: float = 0.02
    house_growth_rate: float = 0.02

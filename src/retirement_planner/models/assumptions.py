"""Economic assumption models."""

from dataclasses import dataclass


@dataclass(slots=True)
class EconomicAssumptions:
    """Core configurable rates for projections."""

    inflation_rate: float = 0.02
    investment_return_rate: float = 0.05
    salary_growth_rate: float = 0.02
    house_growth_rate: float = 0.02
    cpp_max_annual_benefit: float = 17_200.0
    oas_max_annual_benefit: float = 8_820.0

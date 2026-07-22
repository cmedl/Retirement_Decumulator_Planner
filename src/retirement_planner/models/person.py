"""Person-level domain models."""

from dataclasses import dataclass, field
from datetime import date


@dataclass(slots=True)
class PersonProfile:
    """Core person attributes used by projection engines."""

    name: str
    date_of_birth: date
    retirement_date: date
    salary_start: float = 0.0
    salary_growth_rate: float = 0.02
    annual_salary_overrides: dict[int, float] = field(default_factory=dict)
    cpp_start_age: int = 70
    oas_start_age: int = 65
    cpp_percent_of_max: float = 1.0
    oas_percent_of_max: float = 1.0

"""Defined benefit pension models."""

from dataclasses import dataclass
from datetime import date


@dataclass(slots=True)
class DefinedBenefitPension:
    """Provider-agnostic pension contract."""

    owner_name: str
    provider_name: str
    start_date: date
    monthly_lifetime_amount: float
    monthly_bridge_amount: float = 0.0
    bridge_end_age: int | None = None
    enrolment_date: date | None = None
    contributory_service_years: float | None = None
    eligibility_service_years: float | None = None

"""Residence and property models."""

from dataclasses import dataclass


@dataclass(slots=True)
class Residence:
    """Primary residence inputs for planning and reporting."""

    description: str
    current_value: float
    annual_growth_rate: float | None = None

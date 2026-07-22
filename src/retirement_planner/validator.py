"""Validation utilities for phase 0 contracts."""

from datetime import date
from pathlib import Path

from retirement_planner.config import PlannerConfig
from retirement_planner.models import HouseholdPlan, PersonProfile


class ValidationError(ValueError):
    """Raised when planning inputs fail validation."""


def _validate_person(person: PersonProfile, today: date) -> list[str]:
    errors: list[str] = []
    if not person.name.strip():
        errors.append("person.name must not be empty")
    if person.date_of_birth >= today:
        errors.append(f"{person.name}: date_of_birth must be in the past")
    if person.retirement_date <= person.date_of_birth:
        errors.append(f"{person.name}: retirement_date must be after date_of_birth")
    if person.salary_start < 0:
        errors.append(f"{person.name}: salary_start must be non-negative")
    if not 0.0 <= person.cpp_percent_of_max <= 1.5:
        errors.append(f"{person.name}: cpp_percent_of_max must be between 0.0 and 1.5")
    if not 0.0 <= person.oas_percent_of_max <= 1.5:
        errors.append(f"{person.name}: oas_percent_of_max must be between 0.0 and 1.5")
    if person.cpp_start_age < 60 or person.cpp_start_age > 70:
        errors.append(f"{person.name}: cpp_start_age must be between 60 and 70")
    if person.oas_start_age < 65 or person.oas_start_age > 70:
        errors.append(f"{person.name}: oas_start_age must be between 65 and 70")
    return errors


def _validate_data_dir(config: PlannerConfig, project_root: Path | None) -> list[str]:
    errors: list[str] = []
    resolved = config.resolve_data_dir(project_root=project_root)
    if resolved.exists() and not resolved.is_dir():
        errors.append(f"Configured data_dir must be a directory or symlink to one: {resolved}")
    return errors


def validate_phase0_inputs(
    household: HouseholdPlan,
    config: PlannerConfig,
    project_root: Path | None = None,
    today: date | None = None,
) -> None:
    """Validate phase 0 inputs and ensure data directory is available."""
    now = today or date.today()
    errors: list[str] = []

    if not household.people:
        errors.append("household.people must include at least one person")

    for person in household.people:
        errors.extend(_validate_person(person, now))

    if config.end_year < config.start_year:
        errors.append("config.end_year must be >= config.start_year")

    assumptions = config.assumptions
    if assumptions.inflation_rate <= -1.0:
        errors.append("assumptions.inflation_rate must be greater than -1.0")
    if assumptions.investment_return_rate <= -1.0:
        errors.append("assumptions.investment_return_rate must be greater than -1.0")
    if assumptions.salary_growth_rate <= -1.0:
        errors.append("assumptions.salary_growth_rate must be greater than -1.0")
    if assumptions.house_growth_rate <= -1.0:
        errors.append("assumptions.house_growth_rate must be greater than -1.0")

    errors.extend(_validate_data_dir(config, project_root=project_root))

    if errors:
        raise ValidationError("\n".join(errors))

    config.ensure_data_dir(project_root=project_root)

from datetime import date
from pathlib import Path

import pytest

from retirement_planner.config import PlannerConfig
from retirement_planner.models import EconomicAssumptions, HouseholdPlan, PersonProfile, build_yearly_timeline
from retirement_planner.validator import ValidationError, validate_phase0_inputs


def _sample_person() -> PersonProfile:
    return PersonProfile(
        name="Chris",
        date_of_birth=date(1980, 5, 1),
        retirement_date=date(2040, 7, 1),
        salary_start=120_000,
    )


def test_build_yearly_timeline_includes_age_and_inflation() -> None:
    timeline = build_yearly_timeline(
        people=[_sample_person()],
        start_year=2026,
        end_year=2028,
        inflation_rate=0.02,
    )

    assert len(timeline) == 3
    assert timeline[0].year == 2026
    assert timeline[0].inflation_index == pytest.approx(1.0)
    assert timeline[1].inflation_index == pytest.approx(1.02)
    assert timeline[2].ages_at_year_end["Chris"] == 48


def test_config_resolve_data_dir_relative_to_project_root(tmp_path: Path) -> None:
    config = PlannerConfig(data_dir=Path("data"))
    resolved = config.resolve_data_dir(project_root=tmp_path)
    assert resolved == (tmp_path / "data").resolve(strict=False)


def test_validate_phase0_inputs_creates_data_dir(tmp_path: Path) -> None:
    config = PlannerConfig(
        start_year=2026,
        end_year=2030,
        assumptions=EconomicAssumptions(),
        data_dir=Path("data"),
    )
    household = HouseholdPlan(people=[_sample_person()])

    validate_phase0_inputs(household=household, config=config, project_root=tmp_path)

    assert (tmp_path / "data").exists()
    assert (tmp_path / "data").is_dir()


def test_validate_phase0_inputs_rejects_bad_person() -> None:
    bad_person = PersonProfile(
        name="",
        date_of_birth=date(2030, 1, 1),
        retirement_date=date(2029, 1, 1),
    )
    household = HouseholdPlan(people=[bad_person])
    config = PlannerConfig()

    with pytest.raises(ValidationError):
        validate_phase0_inputs(
            household=household,
            config=config,
            today=date(2026, 1, 1),
        )

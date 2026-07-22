from pathlib import Path

import pytest

from retirement_planner.models import ACCOUNT_TYPE_VALUES
from retirement_planner.inputs import InputFileError, load_plan_from_toml, summarize_loaded_plan


def test_load_plan_from_toml_reads_household_and_config(tmp_path: Path) -> None:
    data_dir = tmp_path / "my_retirement_data"
    data_dir.mkdir()
    input_file = tmp_path / "master_data.toml"
    input_file.write_text(
        """
[data]
base_dir = "my_retirement_data"

[files]
config = "config.toml"
people = "people.toml"
accounts = "accounts.toml"
pensions = "pensions.toml"
section7 = "section7.toml"
residence = "residence.toml"
""".strip(),
        encoding="utf-8",
    )

    (data_dir / "config.toml").write_text(
        """
[config]
start_year = 2026
end_year = 2028
run_date = "2026-07-22"

[assumptions]
inflation_rate = 0.02
investment_return_rate = 0.05
salary_growth_rate = 0.02
house_growth_rate = 0.03
""".strip(),
        encoding="utf-8",
    )
    (data_dir / "people.toml").write_text(
        """
[[people]]
name = "Chris"
date_of_birth = "1980-05-01"
retirement_date = "2040-07-01"
salary_start = 120000
cpp_start_age = 70
oas_start_age = 65
""".strip(),
        encoding="utf-8",
    )
    (data_dir / "accounts.toml").write_text(
        """
[[accounts]]
owner_name = "Chris"
account_type = "rrsp"
balance = 250000
""".strip(),
        encoding="utf-8",
    )
    (data_dir / "pensions.toml").write_text(
        """
[[pensions]]
owner_name = "Chris"
provider_name = "HOOPP"
start_date = "2040-07-01"
monthly_lifetime_amount = 3200
monthly_bridge_amount = 700
bridge_end_age = 65
""".strip(),
        encoding="utf-8",
    )
    (data_dir / "section7.toml").write_text(
        """
[section7_obligation]
payer_name = "Chris"
payer_gross_income = 120000
other_party_gross_income = 50000
annual_expense = 12000
indexed_to_inflation = true
""".strip(),
        encoding="utf-8",
    )
    (data_dir / "residence.toml").write_text(
        """
[residence]
description = "Primary residence"
current_value = 950000
annual_growth_rate = 0.02
""".strip(),
        encoding="utf-8",
    )

    config, household = load_plan_from_toml(input_file, project_root=tmp_path)
    summary = summarize_loaded_plan(config, household)

    assert config.start_year == 2026
    assert config.data_dir == data_dir.resolve(strict=False)
    assert len(household.people) == 1
    assert household.accounts[0].balance == 250000
    assert household.pensions[0].provider_name == "HOOPP"
    assert household.residence is not None
    assert summary["people"] == ["Chris"]
    assert summary["has_section7_obligation"] is True
    assert household.section7_obligation is not None
    assert household.section7_obligation.payer_share_fraction == pytest.approx(120000 / 170000)


def test_load_plan_from_toml_rejects_missing_people(tmp_path: Path) -> None:
    data_dir = tmp_path / "my_retirement_data"
    data_dir.mkdir()
    input_file = tmp_path / "master_data.toml"
    input_file.write_text(
        """
[data]
base_dir = "my_retirement_data"

[files]
people = "people.toml"
""".strip(),
        encoding="utf-8",
    )
    (data_dir / "people.toml").write_text("", encoding="utf-8")

    with pytest.raises(InputFileError, match=r"At least one \[\[people\]\] entry is required"):
        load_plan_from_toml(input_file, project_root=tmp_path)


def test_account_type_values_are_canonical() -> None:
    assert ACCOUNT_TYPE_VALUES == (
        "rrsp",
        "spousal_rrsp",
        "tfsa",
        "non_registered",
    )


def test_load_plan_from_toml_rejects_unknown_account_type(tmp_path: Path) -> None:
    data_dir = tmp_path / "my_retirement_data"
    data_dir.mkdir()
    input_file = tmp_path / "master_data.toml"
    input_file.write_text(
        """
[data]
base_dir = "my_retirement_data"

[files]
people = "people.toml"
accounts = "accounts.toml"
""".strip(),
        encoding="utf-8",
    )
    (data_dir / "people.toml").write_text(
        """
[[people]]
name = "Chris"
date_of_birth = "1980-05-01"
retirement_date = "2040-07-01"
""".strip(),
        encoding="utf-8",
    )
    (data_dir / "accounts.toml").write_text(
        """
[[accounts]]
owner_name = "Chris"
account_type = "cash"
balance = 1000
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(InputFileError, match=r"Invalid account_type 'cash'"):
        load_plan_from_toml(input_file, project_root=tmp_path)


def test_section7_share_fraction_requires_positive_total_income() -> None:
    from retirement_planner.models.household import Section7Obligation

    obligation = Section7Obligation(
        payer_name="Chris",
        payer_gross_income=0,
        other_party_gross_income=0,
        annual_expense=1000,
    )

    with pytest.raises(ValueError, match=r"must total more than zero"):
        _ = obligation.payer_share_fraction

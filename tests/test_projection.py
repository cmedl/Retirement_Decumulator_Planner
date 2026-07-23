from datetime import date
import zipfile

import pytest

from retirement_planner.config import PlannerConfig
from retirement_planner.models import (
    AccountBalance,
    AccountType,
    DefinedBenefitPension,
    EconomicAssumptions,
    HouseholdPlan,
    PersonProfile,
    Residence,
    Section7Obligation,
)
from retirement_planner.projection import format_household_projection_table, project_household, write_projection_output


def _projection_household() -> HouseholdPlan:
    return HouseholdPlan(
        people=[
            PersonProfile(
                name="Chris",
                date_of_birth=date(1972, 10, 4),
                retirement_date=date(2032, 10, 4),
                salary_start=195_000,
                annual_salary_overrides={2030: 150_000},
                cpp_start_age=70,
                oas_start_age=65,
                cpp_percent_of_max=0.96,
                oas_percent_of_max=1.0,
            ),
            PersonProfile(
                name="Katie",
                date_of_birth=date(1976, 9, 12),
                retirement_date=date(2034, 7, 1),
                salary_start=120_000,
                cpp_start_age=70,
                oas_start_age=65,
                cpp_percent_of_max=0.85,
                oas_percent_of_max=1.0,
            ),
        ],
        accounts=[
            AccountBalance(owner_name="Chris", account_type=AccountType.RRSP, balance=1_120_000),
            AccountBalance(owner_name="Chris", account_type=AccountType.TFSA, balance=41_000),
            AccountBalance(owner_name="Chris", account_type=AccountType.NON_REGISTERED, balance=350),
            AccountBalance(owner_name="Katie", account_type=AccountType.SPOUSAL_RRSP, balance=7_000),
            AccountBalance(owner_name="Katie", account_type=AccountType.TFSA, balance=18_000),
        ],
        pensions=[
            DefinedBenefitPension(
                owner_name="Katie",
                provider_name="HOOPP",
                start_date=date(2034, 7, 1),
                monthly_lifetime_amount=3_200,
                monthly_bridge_amount=700,
                bridge_end_age=65,
                enrolment_date=date(2004, 5, 3),
                contributory_service_years=21.83,
                eligibility_service_years=22.08,
            )
        ],
        section7_obligation=Section7Obligation(
            payer_name="Chris",
            payer_gross_income=195_000,
            other_party_gross_income=130_000,
            annual_expense=38_000,
        ),
        residence=Residence(description="Primary residence", current_value=950_000, annual_growth_rate=0.02),
    )


def test_project_household_builds_yearly_rows() -> None:
    config = PlannerConfig(
        start_year=2026,
        end_year=2028,
        assumptions=EconomicAssumptions(
            inflation_rate=0.02,
            investment_return_rate=0.05,
            salary_growth_rate=0.02,
            house_growth_rate=0.02,
        ),
    )

    result = project_household(_projection_household(), config)

    assert [row.year for row in result.household_rows] == [2026, 2027, 2028]
    assert result.household_rows[0].gross_income_total > 0
    assert result.household_rows[0].section7_expense_total > 0
    assert result.household_rows[-1].house_valuation > result.household_rows[0].house_valuation


def test_project_household_projects_account_balances() -> None:
    config = PlannerConfig(start_year=2026, end_year=2026, assumptions=EconomicAssumptions())
    household = _projection_household()

    result = project_household(household, config)

    tfsa_total = result.household_rows[0].tfsa_total
    assert tfsa_total == pytest.approx((41_000 + 18_000) * (1 + config.assumptions.investment_return_rate))


def test_projection_table_includes_summary_header() -> None:
    config = PlannerConfig(start_year=2026, end_year=2026, assumptions=EconomicAssumptions())
    result = project_household(_projection_household(), config)

    table = format_household_projection_table(result, limit=1)
    assert "gross_income_total" in table
    assert "2026" in table


def test_write_projection_output_csv(tmp_path) -> None:
    config = PlannerConfig(start_year=2026, end_year=2026, assumptions=EconomicAssumptions())
    result = project_household(_projection_household(), config)

    output_path = write_projection_output(result, tmp_path / "projection.csv")

    assert output_path.exists()
    lines = output_path.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith(",Age,Age,Capital Assets,Capital Assets,Capital Assets,Capital Assets"
    )
    assert lines[1].startswith("Year,Chris,Katie,Chris Non-Registered")
    assert "Estate after tax" in lines[0]

    assert "Chris Spousal RRSP" not in lines[1]
    assert "Katie Spousal RRSP" in lines[1]

    data_cells = lines[2].split(",")
    # Year and ages are integer by design; all dollar amounts are exported as whole dollars.
    assert "." not in data_cells[0]
    assert "." not in data_cells[1]
    assert "." not in data_cells[2]
    assert all("." not in cell for cell in data_cells[3:])


def test_write_projection_output_ods(tmp_path) -> None:
    config = PlannerConfig(start_year=2026, end_year=2026, assumptions=EconomicAssumptions())
    result = project_household(_projection_household(), config)

    output_path = write_projection_output(result, tmp_path / "projection.ods")

    assert output_path.exists()
    with zipfile.ZipFile(output_path) as archive:
        assert "content.xml" in archive.namelist()
        content_xml = archive.read("content.xml").decode("utf-8")
        assert "Capital Assets" in content_xml
        assert "Chris Non-Registered" in content_xml
        assert "Chris Spousal RRSP" not in content_xml
        assert "Katie Spousal RRSP" in content_xml
        assert "Estate after tax" in content_xml
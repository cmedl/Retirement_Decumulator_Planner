from datetime import date
import zipfile

import pytest

from retirement_planner.config import PlannerConfig
from retirement_planner.models import (
    AccountBalance,
    AccountType,
    ContributionFrequency,
    ContributionRule,
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
        run_date=date(2026, 1, 1),
    )

    result = project_household(_projection_household(), config)

    assert [row.year for row in result.household_rows] == [2026, 2027, 2028]
    assert result.household_rows[0].gross_income_total > 0
    assert result.household_rows[0].total_tax > 0
    assert result.household_rows[0].section7_expense_total > 0
    assert result.household_rows[-1].house_valuation > result.household_rows[0].house_valuation


def test_project_household_projects_account_balances() -> None:
    config = PlannerConfig(
        start_year=2026,
        end_year=2026,
        run_date=date(2026, 1, 1),
        assumptions=EconomicAssumptions(),
    )
    household = _projection_household()

    result = project_household(household, config)

    tfsa_total = result.household_rows[0].tfsa_total
    assert tfsa_total == pytest.approx((41_000 + 18_000) * (1 + config.assumptions.investment_return_rate))


def test_projection_table_includes_summary_header() -> None:
    config = PlannerConfig(
        start_year=2026,
        end_year=2026,
        run_date=date(2026, 1, 1),
        assumptions=EconomicAssumptions(),
    )
    result = project_household(_projection_household(), config)

    table = format_household_projection_table(result, limit=1)
    assert "gross_income_total" in table
    assert "2026" in table


def test_person_rows_include_tax_breakdown() -> None:
    config = PlannerConfig(
        start_year=2026,
        end_year=2026,
        run_date=date(2026, 1, 1),
        assumptions=EconomicAssumptions(),
    )

    result = project_household(_projection_household(), config)
    chris_row = next(r for r in result.person_rows if r.person_name == "Chris" and r.year == 2026)

    assert chris_row.federal_tax > 0
    assert chris_row.ontario_tax > 0
    assert chris_row.total_tax == pytest.approx(
        chris_row.federal_tax + chris_row.ontario_tax + chris_row.oas_clawback
    )
    assert chris_row.net_income == pytest.approx(
        chris_row.gross_income - chris_row.total_tax - chris_row.section7_expense
    )


def test_pre_retirement_contribution_applied_and_post_retirement_stops() -> None:
    config = PlannerConfig(
        start_year=2026,
        end_year=2034,
        assumptions=EconomicAssumptions(
            inflation_rate=0.02,
            investment_return_rate=0.00,
            salary_growth_rate=0.00,
            house_growth_rate=0.00,
        ),
        run_date=date(2026, 1, 1),
    )
    household = HouseholdPlan(
        people=[
            PersonProfile(
                name="Chris",
                date_of_birth=date(1972, 10, 4),
                retirement_date=date(2032, 10, 4),
                salary_start=100_000,
                salary_growth_rate=0.0,
            )
        ],
        accounts=[
            AccountBalance(
                owner_name="Chris",
                account_type=AccountType.TFSA,
                balance=10_000,
                contribution=ContributionRule(
                    frequency=ContributionFrequency.YEARLY,
                    amount=1_200,
                ),
            )
        ],
    )

    result = project_household(household, config)
    row_2026 = next(r for r in result.account_rows if r.year == 2026 and r.account_type == AccountType.TFSA)
    row_2034 = next(r for r in result.account_rows if r.year == 2034 and r.account_type == AccountType.TFSA)

    assert row_2026.closing_balance == pytest.approx(11_200)
    assert row_2034.closing_balance == pytest.approx(row_2034.opening_balance)


def test_percent_income_contribution_uses_named_income() -> None:
    config = PlannerConfig(
        start_year=2026,
        end_year=2026,
        assumptions=EconomicAssumptions(
            inflation_rate=0.02,
            investment_return_rate=0.00,
            salary_growth_rate=0.00,
            house_growth_rate=0.00,
        ),
        run_date=date(2026, 1, 1),
    )
    household = HouseholdPlan(
        people=[
            PersonProfile(
                name="Chris",
                date_of_birth=date(1972, 10, 4),
                retirement_date=date(2032, 10, 4),
                salary_start=100_000,
                salary_growth_rate=0.0,
            )
        ],
        accounts=[
            AccountBalance(
                owner_name="Chris",
                account_type=AccountType.NON_REGISTERED,
                balance=0,
                contribution=ContributionRule(
                    frequency=ContributionFrequency.PERCENT_OF_INCOME_ANNUAL,
                    percent_of_income=0.05,
                    income_person="Chris",
                ),
            )
        ],
    )

    result = project_household(household, config)
    row_2026 = next(
        r for r in result.account_rows if r.year == 2026 and r.account_type == AccountType.NON_REGISTERED
    )

    assert row_2026.closing_balance == pytest.approx(5_000)


def test_write_projection_output_csv(tmp_path) -> None:
    config = PlannerConfig(
        start_year=2026,
        end_year=2026,
        run_date=date(2026, 1, 1),
        assumptions=EconomicAssumptions(),
    )
    result = project_household(_projection_household(), config)

    output_path = write_projection_output(result, tmp_path / "projection.csv")
    cashflow_path = tmp_path / "projection_cashflow.csv"

    assert output_path.exists()
    assert cashflow_path.exists()
    lines = output_path.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith(",Age,Age,Capital Assets,Capital Assets,Capital Assets,Capital Assets"
    )
    assert lines[1].startswith("Year,Chris,Katie,Chris Non-Registered")
    assert "Income Tax" in lines[0]
    assert "After-Tax Income" in lines[0]
    assert "Estate after tax" in lines[0]

    assert "Chris Spousal RRSP" not in lines[1]
    assert "Katie Spousal RRSP" in lines[1]

    data_cells = lines[2].split(",")
    # Year and ages are integer by design; all dollar amounts are exported as whole dollars.
    assert "." not in data_cells[0]
    assert "." not in data_cells[1]
    assert "." not in data_cells[2]
    assert all("." not in cell for cell in data_cells[3:])

    cashflow_lines = cashflow_path.read_text(encoding="utf-8").splitlines()
    assert "Chris Employment Income" in cashflow_lines[0]
    assert "Chris Income Tax" in cashflow_lines[0]
    assert "Chris Federal Tax" not in cashflow_lines[0]
    assert "Chris Ontario Tax" not in cashflow_lines[0]
    assert "Household Income Tax" in cashflow_lines[0]
    assert "Average Tax Rate (%)" in cashflow_lines[0]


def test_write_projection_output_ods(tmp_path) -> None:
    config = PlannerConfig(
        start_year=2026,
        end_year=2026,
        run_date=date(2026, 1, 1),
        assumptions=EconomicAssumptions(),
    )
    result = project_household(_projection_household(), config)

    output_path = write_projection_output(result, tmp_path / "projection.ods")

    assert output_path.exists()
    with zipfile.ZipFile(output_path) as archive:
        assert "content.xml" in archive.namelist()
        content_xml = archive.read("content.xml").decode("utf-8")
        assert "Capital Assets" in content_xml
        assert 'table:name="CashFlow"' in content_xml
        assert "Average Tax Rate (%)" in content_xml
        assert "Chris Non-Registered" in content_xml
        assert "Chris Spousal RRSP" not in content_xml
        assert "Katie Spousal RRSP" in content_xml
        assert "Estate after tax" in content_xml


def test_first_year_growth_and_contribution_are_prorated_from_run_date() -> None:
    config = PlannerConfig(
        start_year=2026,
        end_year=2026,
        run_date=date(2026, 7, 22),
        assumptions=EconomicAssumptions(
            inflation_rate=0.02,
            investment_return_rate=0.05,
            salary_growth_rate=0.00,
            house_growth_rate=0.00,
        ),
    )
    household = HouseholdPlan(
        people=[
            PersonProfile(
                name="Chris",
                date_of_birth=date(1972, 10, 4),
                retirement_date=date(2032, 10, 4),
                salary_start=100_000,
                salary_growth_rate=0.0,
            )
        ],
        accounts=[
            AccountBalance(
                owner_name="Chris",
                account_type=AccountType.TFSA,
                balance=10_000,
                contribution=ContributionRule(
                    frequency=ContributionFrequency.YEARLY,
                    amount=1_200,
                ),
            )
        ],
    )

    result = project_household(household, config)
    account_row = next(r for r in result.account_rows if r.year == 2026)
    projected_fraction = (date(2027, 1, 1) - date(2026, 7, 22)).days / 365

    expected_growth = 10_000 * 0.05 * projected_fraction
    expected_contribution = 1_200 * projected_fraction
    assert account_row.closing_balance == pytest.approx(10_000 + expected_growth + expected_contribution)


def test_full_year_salary_is_not_day_short() -> None:
    config = PlannerConfig(
        start_year=2030,
        end_year=2030,
        run_date=date(2030, 1, 1),
        assumptions=EconomicAssumptions(
            inflation_rate=0.02,
            investment_return_rate=0.0,
            salary_growth_rate=0.0,
            house_growth_rate=0.0,
        ),
    )
    household = HouseholdPlan(
        people=[
            PersonProfile(
                name="Chris",
                date_of_birth=date(1972, 10, 4),
                retirement_date=date(2032, 10, 4),
                salary_start=100_000,
                salary_growth_rate=0.0,
                annual_salary_overrides={2030: 150_000},
            )
        ]
    )

    result = project_household(household, config)
    row = next(r for r in result.person_rows if r.person_name == "Chris" and r.year == 2030)

    assert row.employment_income == pytest.approx(150_000)


def test_salary_override_becomes_new_baseline() -> None:
    config = PlannerConfig(
        start_year=2030,
        end_year=2031,
        run_date=date(2030, 1, 1),
        assumptions=EconomicAssumptions(
            inflation_rate=0.02,
            investment_return_rate=0.0,
            salary_growth_rate=0.02,
            house_growth_rate=0.0,
        ),
    )
    household = HouseholdPlan(
        people=[
            PersonProfile(
                name="Chris",
                date_of_birth=date(1972, 10, 4),
                retirement_date=date(2032, 10, 4),
                salary_start=195_000,
                salary_growth_rate=0.02,
                annual_salary_overrides={2030: 150_000},
            )
        ]
    )

    result = project_household(household, config)
    row_2030 = next(r for r in result.person_rows if r.person_name == "Chris" and r.year == 2030)
    row_2031 = next(r for r in result.person_rows if r.person_name == "Chris" and r.year == 2031)

    assert row_2030.employment_income == pytest.approx(150_000)
    assert row_2031.employment_income == pytest.approx(150_000 * 1.02)


def test_oas_clawback_applies_above_threshold() -> None:
    config = PlannerConfig(
        start_year=2026,
        end_year=2026,
        run_date=date(2026, 1, 1),
        assumptions=EconomicAssumptions(
            inflation_rate=0.02,
            investment_return_rate=0.0,
            salary_growth_rate=0.0,
            house_growth_rate=0.0,
        ),
    )
    household = HouseholdPlan(
        people=[
            PersonProfile(
                name="Chris",
                date_of_birth=date(1946, 1, 1),
                retirement_date=date(2020, 1, 1),
                salary_start=0.0,
                salary_growth_rate=0.0,
                cpp_start_age=60,
                oas_start_age=65,
                cpp_percent_of_max=1.0,
                oas_percent_of_max=1.0,
            )
        ],
        pensions=[
            DefinedBenefitPension(
                owner_name="Chris",
                provider_name="Demo",
                start_date=date(2020, 1, 1),
                monthly_lifetime_amount=9_000,
            )
        ],
    )

    result = project_household(household, config)
    row = next(r for r in result.person_rows if r.person_name == "Chris" and r.year == 2026)

    assert row.oas_income > 0
    assert row.oas_clawback > 0
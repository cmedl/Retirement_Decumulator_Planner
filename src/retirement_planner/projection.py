"""Deterministic Phase 1B projection engine."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from calendar import isleap
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile

from retirement_planner.config import PlannerConfig
from retirement_planner.ledger import HOUSEHOLD_LEDGER_COLUMNS, PERSON_LEDGER_COLUMNS
from retirement_planner.models import (
    AccountBalance,
    AccountType,
    DefinedBenefitPension,
    HouseholdPlan,
    PersonProfile,
    Residence,
    age_on_date,
    TimelineYear,
    build_yearly_timeline,
)
from retirement_planner.tax import compute_income_tax


@dataclass(slots=True)
class PersonProjectionRow:
    year: int
    person_name: str
    employment_income: float
    defined_benefit_pension_income: float
    cpp_income: float
    oas_income: float
    gross_income: float
    federal_tax: float
    ontario_tax: float
    oas_clawback: float
    total_tax: float
    section7_expense: float
    net_income: float


@dataclass(slots=True)
class AccountProjectionRow:
    year: int
    owner_name: str
    account_type: AccountType
    opening_balance: float
    investment_growth: float
    closing_balance: float


@dataclass(slots=True)
class HouseholdProjectionRow:
    year: int
    gross_income_total: float
    total_tax: float
    section7_expense_total: float
    net_income_total: float
    house_valuation: float
    rrsp_total: float
    spousal_rrsp_total: float
    tfsa_total: float
    non_registered_total: float
    estate_estimated_taxable_amount: float


@dataclass(slots=True)
class ProjectionResult:
    timeline: list[TimelineYear]
    person_rows: list[PersonProjectionRow]
    account_rows: list[AccountProjectionRow]
    household_rows: list[HouseholdProjectionRow]


@dataclass(slots=True, frozen=True)
class ProjectionOutputColumn:
    key: str
    header_row1: str
    header_row2: str
    is_money: bool


def _days_in_year(year: int) -> int:
    return 366 if isleap(year) else 365


def _year_fraction(start_date: date, end_date: date, year: int) -> float:
    year_start = date(year, 1, 1)
    year_end = date(year, 12, 31)
    interval_start = max(start_date, year_start)
    interval_end = min(end_date, year_end)
    if interval_end < interval_start:
        return 0.0
    # Inclusive day count so Jan 1 through Dec 31 is exactly 1.0.
    return ((interval_end - interval_start).days + 1) / _days_in_year(year)


def _salary_base_for_year(person: PersonProfile, year: int, start_year: int) -> float:
    """Return full-year salary base with overrides as carry-forward baseline changes."""
    override_years = [override_year for override_year in person.annual_salary_overrides if override_year <= year]
    if not override_years:
        return person.salary_start * (1 + person.salary_growth_rate) ** (year - start_year)

    latest_override_year = max(override_years)
    latest_override_salary = person.annual_salary_overrides[latest_override_year]
    return latest_override_salary * (1 + person.salary_growth_rate) ** (year - latest_override_year)


def _projection_year_activity_fraction(year: int, config: PlannerConfig) -> float:
    """Return fraction of a projection year that remains after run_date in start_year."""
    if year < config.start_year:
        return 0.0
    if year > config.start_year:
        return 1.0

    year_start = date(year, 1, 1)
    next_year_start = date(year + 1, 1, 1)
    interval_start = max(config.run_date, year_start)
    if interval_start >= next_year_start:
        return 0.0
    return (next_year_start - interval_start).days / _days_in_year(year)


def _salary_for_year(person: PersonProfile, year: int, config: PlannerConfig) -> float:
    if year < config.start_year:
        return 0.0

    base_salary = _salary_base_for_year(person, year, config.start_year)
    retirement_fraction = _year_fraction(date(year, 1, 1), person.retirement_date, year)
    projection_activity_fraction = _projection_year_activity_fraction(year, config)
    return base_salary * retirement_fraction * projection_activity_fraction


def _full_year_salary_base(person: PersonProfile, year: int, start_year: int) -> float:
    """Return salary basis before retirement proration for contribution rules."""
    if year < start_year:
        return 0.0
    return _salary_base_for_year(person, year, start_year)


def _benefit_start_date(person: PersonProfile, start_age: int) -> date:
    return date(person.date_of_birth.year + start_age, person.date_of_birth.month, person.date_of_birth.day)


def _cpp_income_for_year(person: PersonProfile, year: int, config: PlannerConfig) -> float:
    start_date = _benefit_start_date(person, person.cpp_start_age)
    if year < start_date.year:
        return 0.0

    annual_benefit = config.assumptions.cpp_max_annual_benefit * person.cpp_percent_of_max
    projection_activity_fraction = _projection_year_activity_fraction(year, config)
    if year > start_date.year:
        return annual_benefit * projection_activity_fraction
    return annual_benefit * _year_fraction(start_date, date(year, 12, 31), year) * projection_activity_fraction


def _oas_income_for_year(person: PersonProfile, year: int, config: PlannerConfig) -> float:
    start_date = _benefit_start_date(person, person.oas_start_age)
    if year < start_date.year:
        return 0.0

    annual_benefit = config.assumptions.oas_max_annual_benefit * person.oas_percent_of_max
    projection_activity_fraction = _projection_year_activity_fraction(year, config)
    if year > start_date.year:
        return annual_benefit * projection_activity_fraction
    return annual_benefit * _year_fraction(start_date, date(year, 12, 31), year) * projection_activity_fraction


def _pension_income_for_year(
    pension: DefinedBenefitPension,
    person: PersonProfile,
    year: int,
    config: PlannerConfig,
) -> float:
    if year < pension.start_date.year:
        return 0.0

    annual_lifetime = pension.monthly_lifetime_amount * 12
    age_at_year_end = age_on_date(person.date_of_birth, date(year, 12, 31))
    bridge_active = pension.bridge_end_age is None or age_at_year_end < pension.bridge_end_age
    bridge_amount = pension.monthly_bridge_amount * 12 if bridge_active else 0.0
    projection_activity_fraction = _projection_year_activity_fraction(year, config)

    if year > pension.start_date.year:
        return (annual_lifetime + bridge_amount) * projection_activity_fraction

    return (annual_lifetime + bridge_amount) * _year_fraction(pension.start_date, date(year, 12, 31), year) * projection_activity_fraction


def _project_accounts(
    accounts: list[AccountBalance],
    timeline_years: list[TimelineYear],
    config: PlannerConfig,
    people_by_name: dict[str, PersonProfile],
    employment_income_by_year_and_person: dict[int, dict[str, float]],
) -> list[AccountProjectionRow]:
    rows: list[AccountProjectionRow] = []
    balances = {
        (account.owner_name, account.account_type): account.balance for account in accounts
    }

    for timeline_year in timeline_years:
        year_income = employment_income_by_year_and_person.get(timeline_year.year, {})
        projection_activity_fraction = _projection_year_activity_fraction(timeline_year.year, config)
        for account in accounts:
            key = (account.owner_name, account.account_type)
            opening_balance = balances[key]
            investment_growth = (
                opening_balance
                * config.assumptions.investment_return_rate
                * projection_activity_fraction
            )

            contribution_amount = 0.0
            owner = people_by_name.get(account.owner_name)
            if owner is not None and account.contribution is not None:
                if timeline_year.year < owner.retirement_date.year:
                    pre_retirement_fraction = 1.0
                elif timeline_year.year > owner.retirement_date.year:
                    pre_retirement_fraction = 0.0
                else:
                    pre_retirement_fraction = _year_fraction(
                        date(timeline_year.year, 1, 1),
                        owner.retirement_date,
                        timeline_year.year,
                    )
                if pre_retirement_fraction > 0:
                    annual_base = account.contribution.annual_base_amount(year_income)
                    contribution_amount = annual_base * pre_retirement_fraction * projection_activity_fraction

            closing_balance = opening_balance + investment_growth + contribution_amount
            balances[key] = closing_balance
            rows.append(
                AccountProjectionRow(
                    year=timeline_year.year,
                    owner_name=account.owner_name,
                    account_type=account.account_type,
                    opening_balance=opening_balance,
                    investment_growth=investment_growth + contribution_amount,
                    closing_balance=closing_balance,
                )
            )

    return rows


def _project_residence(residence: Residence | None, timeline_years: list[TimelineYear], config: PlannerConfig) -> dict[int, float]:
    projected_values: dict[int, float] = {}
    if residence is None:
        return projected_values

    value = residence.current_value
    for timeline_year in timeline_years:
        projection_activity_fraction = _projection_year_activity_fraction(timeline_year.year, config)
        value *= 1 + (config.assumptions.house_growth_rate * projection_activity_fraction)
        projected_values[timeline_year.year] = value

    return projected_values


def project_household(household: HouseholdPlan, config: PlannerConfig) -> ProjectionResult:
    """Build a deterministic year-by-year projection from loaded Phase 1 inputs."""
    timeline = build_yearly_timeline(
        people=household.people,
        start_year=config.start_year,
        end_year=config.end_year,
        inflation_rate=config.assumptions.inflation_rate,
    )

    people_by_name = {person.name: person for person in household.people}
    employment_income_by_year_and_person: dict[int, dict[str, float]] = {}
    full_year_salary_base_by_year_and_person: dict[int, dict[str, float]] = {}
    for timeline_year in timeline:
        employment_income_by_year_and_person[timeline_year.year] = {
            person.name: _salary_for_year(person, timeline_year.year, config)
            for person in household.people
        }
        full_year_salary_base_by_year_and_person[timeline_year.year] = {
            person.name: _full_year_salary_base(person, timeline_year.year, config.start_year)
            for person in household.people
        }

    account_rows = _project_accounts(
        household.accounts,
        timeline,
        config,
        people_by_name=people_by_name,
        employment_income_by_year_and_person=full_year_salary_base_by_year_and_person,
    )
    residence_values = _project_residence(household.residence, timeline, config)

    person_rows: list[PersonProjectionRow] = []
    household_rows: list[HouseholdProjectionRow] = []

    section7_obligation = household.section7_obligation
    payer_name = section7_obligation.payer_name if section7_obligation else None

    for timeline_year in timeline:
        annual_person_rows: list[PersonProjectionRow] = []
        for person in household.people:
            employment_income = employment_income_by_year_and_person[timeline_year.year][person.name]
            pension_income = sum(
                _pension_income_for_year(pension, person, timeline_year.year, config)
                for pension in household.pensions
                if pension.owner_name == person.name
            )
            cpp_income = _cpp_income_for_year(person, timeline_year.year, config)
            oas_income = _oas_income_for_year(person, timeline_year.year, config)

            gross_income = employment_income + pension_income + cpp_income + oas_income
            person_age = timeline_year.ages_at_year_end.get(person.name, 0)
            tax_result = compute_income_tax(
                taxable_income=gross_income,
                age=person_age,
                oas_income=oas_income,
                eligible_pension_income=pension_income,
            )

            if section7_obligation and person.name == payer_name:
                section7_expense = section7_obligation.annual_expense * timeline_year.inflation_index * section7_obligation.payer_share_fraction
            elif section7_obligation:
                section7_expense = section7_obligation.annual_expense * timeline_year.inflation_index * (1 - section7_obligation.payer_share_fraction)
            else:
                section7_expense = 0.0

            person_row = PersonProjectionRow(
                year=timeline_year.year,
                person_name=person.name,
                employment_income=employment_income,
                defined_benefit_pension_income=pension_income,
                cpp_income=cpp_income,
                oas_income=oas_income,
                gross_income=gross_income,
                federal_tax=tax_result.federal_tax,
                ontario_tax=tax_result.ontario_tax,
                oas_clawback=tax_result.oas_clawback,
                total_tax=tax_result.total_tax,
                section7_expense=section7_expense,
                net_income=gross_income - tax_result.total_tax - section7_expense,
            )
            annual_person_rows.append(person_row)
            person_rows.append(person_row)

        gross_income_total = sum(row.gross_income for row in annual_person_rows)
        total_tax = sum(row.total_tax for row in annual_person_rows)
        section7_expense_total = sum(row.section7_expense for row in annual_person_rows)
        net_income_total = sum(row.net_income for row in annual_person_rows)

        def _sum_account_type(account_type: AccountType) -> float:
            return sum(
                row.closing_balance
                for row in account_rows
                if row.year == timeline_year.year and row.account_type == account_type
            )

        rrsp_total = _sum_account_type(AccountType.RRSP)
        spousal_rrsp_total = _sum_account_type(AccountType.SPOUSAL_RRSP)
        tfsa_total = _sum_account_type(AccountType.TFSA)
        non_registered_total = _sum_account_type(AccountType.NON_REGISTERED)
        house_valuation = residence_values.get(timeline_year.year, 0.0)
        estate_estimated_taxable_amount = rrsp_total + spousal_rrsp_total + non_registered_total + house_valuation

        household_rows.append(
            HouseholdProjectionRow(
                year=timeline_year.year,
                gross_income_total=gross_income_total,
                total_tax=total_tax,
                section7_expense_total=section7_expense_total,
                net_income_total=net_income_total,
                house_valuation=house_valuation,
                rrsp_total=rrsp_total,
                spousal_rrsp_total=spousal_rrsp_total,
                tfsa_total=tfsa_total,
                non_registered_total=non_registered_total,
                estate_estimated_taxable_amount=estate_estimated_taxable_amount,
            )
        )

    return ProjectionResult(
        timeline=timeline,
        person_rows=person_rows,
        account_rows=account_rows,
        household_rows=household_rows,
    )


def format_household_projection_table(result: ProjectionResult, limit: int | None = None) -> str:
    """Format household projection rows as a compact plain-text table."""
    lines = [
        "year | gross_income_total | section7_expense_total | net_income_total | rrsp_total | tfsa_total | non_registered_total | house_valuation",
        "-" * 120,
    ]
    rows = result.household_rows if limit is None else result.household_rows[:limit]
    for row in rows:
        lines.append(
            f"{row.year} | {row.gross_income_total:.2f} | {row.section7_expense_total:.2f} | {row.net_income_total:.2f} | {row.rrsp_total:.2f} | {row.tfsa_total:.2f} | {row.non_registered_total:.2f} | {row.house_valuation:.2f}"
        )
    return "\n".join(lines)


def projection_header_summary() -> str:
    """Return a compact header summary showing the ledger-backed outputs."""
    return (
        f"person ledger columns: {len(PERSON_LEDGER_COLUMNS)}\n"
        f"household ledger columns: {len(HOUSEHOLD_LEDGER_COLUMNS)}"
    )


def _distinct_people_in_order(result: ProjectionResult) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for row in result.person_rows:
        if row.person_name not in seen:
            seen.add(row.person_name)
            names.append(row.person_name)
    return names


def _account_type_display_name(account_type: AccountType) -> str:
    display_names: dict[AccountType, str] = {
        AccountType.NON_REGISTERED: "Non-Registered",
        AccountType.RRSP: "RRSP",
        AccountType.SPOUSAL_RRSP: "Spousal RRSP",
        AccountType.TFSA: "TFSA",
    }
    return display_names[account_type]


def _build_output_columns(result: ProjectionResult) -> list[ProjectionOutputColumn]:
    people = _distinct_people_in_order(result)
    columns: list[ProjectionOutputColumn] = [
        ProjectionOutputColumn(key="year", header_row1="", header_row2="Year", is_money=False)
    ]

    for person_name in people:
        columns.append(
            ProjectionOutputColumn(
                key=f"age::{person_name}",
                header_row1="Age",
                header_row2=person_name,
                is_money=False,
            )
        )

    account_order = [
        AccountType.NON_REGISTERED,
        AccountType.RRSP,
        AccountType.SPOUSAL_RRSP,
        AccountType.TFSA,
    ]
    for person_name in people:
        present_types = {
            row.account_type
            for row in result.account_rows
            if row.owner_name == person_name
        }
        for account_type in account_order:
            if account_type in present_types:
                columns.append(
                    ProjectionOutputColumn(
                        key=f"account::{person_name}::{account_type.value}",
                        header_row1="Capital Assets",
                        header_row2=f"{person_name} {_account_type_display_name(account_type)}",
                        is_money=True,
                    )
                )

    columns.extend(
        [
            ProjectionOutputColumn(key="house_value", header_row1="House", header_row2="Value", is_money=True),
            ProjectionOutputColumn(key="income_tax", header_row1="Income Tax", header_row2="Total", is_money=True),
            ProjectionOutputColumn(key="after_tax_income", header_row1="After-Tax Income", header_row2="Total", is_money=True),
            ProjectionOutputColumn(key="net_worth", header_row1="Net Worth", header_row2="Amount", is_money=True),
            ProjectionOutputColumn(
                key="estate_before_tax",
                header_row1="Estate before Tax",
                header_row2="Amount",
                is_money=True,
            ),
            ProjectionOutputColumn(key="tax_on_estate", header_row1="Tax on Estate", header_row2="Amount", is_money=True),
            ProjectionOutputColumn(
                key="estate_after_tax",
                header_row1="Estate after tax",
                header_row2="Amount",
                is_money=True,
            ),
        ]
    )
    return columns


def _sum_account_for_year_owner_type(
    result: ProjectionResult,
    year: int,
    owner_name: str,
    account_type: AccountType,
) -> float:
    return sum(
        row.closing_balance
        for row in result.account_rows
        if row.year == year and row.owner_name == owner_name and row.account_type == account_type
    )


def _projection_row_mapping(
    result: ProjectionResult,
    household_row: HouseholdProjectionRow,
    columns: list[ProjectionOutputColumn],
) -> dict[str, object]:
    year = household_row.year
    timeline_entry = next(item for item in result.timeline if item.year == year)

    house_value = household_row.house_valuation
    total_accounts = sum(row.closing_balance for row in result.account_rows if row.year == year)
    net_worth = total_accounts + house_value
    estate_before_tax = net_worth
    tax_on_estate = 0.0
    estate_after_tax = estate_before_tax - tax_on_estate

    def _money(value: float) -> int:
        return int(round(value))

    values: dict[str, object] = {
        "year": year,
        "house_value": _money(house_value),
        "income_tax": _money(household_row.total_tax),
        "after_tax_income": _money(household_row.net_income_total),
        "net_worth": _money(net_worth),
        "estate_before_tax": _money(estate_before_tax),
        "tax_on_estate": _money(tax_on_estate),
        "estate_after_tax": _money(estate_after_tax),
    }

    for column in columns:
        if column.key in values:
            continue
        if column.key.startswith("age::"):
            person_name = column.key.split("::", 1)[1]
            values[column.key] = timeline_entry.ages_at_year_end.get(person_name, 0)
            continue
        if column.key.startswith("account::"):
            _, owner_name, account_type_value = column.key.split("::", 2)
            account_type = AccountType(account_type_value)
            account_value = _sum_account_for_year_owner_type(
                result,
                year,
                owner_name,
                account_type,
            )
            values[column.key] = _money(account_value)

    return values


def _cashflow_headers_and_rows(result: ProjectionResult) -> tuple[list[str], list[list[object]]]:
    people = _distinct_people_in_order(result)
    headers = ["Year"]

    for person_name in people:
        headers.extend(
            [
                f"{person_name} Employment Income",
                f"{person_name} DB Pension",
                f"{person_name} CPP",
                f"{person_name} OAS",
                f"{person_name} Gross Income",
                f"{person_name} OAS Clawback",
                f"{person_name} Income Tax",
                f"{person_name} Average Tax Rate (%)",
            ]
        )

    headers.extend(
        [
            "Household Gross Income",
            "Household Income Tax",
            "Household Average Tax Rate (%)",
            "Section7 Expense Total",
            "Household Net Income",
        ]
    )

    person_rows_by_year_name = {
        (row.year, row.person_name): row
        for row in result.person_rows
    }

    def _money(value: float) -> int:
        return int(round(value))

    rows: list[list[object]] = []
    for household_row in result.household_rows:
        year = household_row.year
        row_values: list[object] = [year]

        for person_name in people:
            person_row = person_rows_by_year_name[(year, person_name)]
            person_avg_tax_rate = (
                (person_row.total_tax / person_row.gross_income) * 100
                if person_row.gross_income > 0
                else 0.0
            )
            row_values.extend(
                [
                    _money(person_row.employment_income),
                    _money(person_row.defined_benefit_pension_income),
                    _money(person_row.cpp_income),
                    _money(person_row.oas_income),
                    _money(person_row.gross_income),
                    _money(person_row.oas_clawback),
                    _money(person_row.total_tax),
                    round(person_avg_tax_rate, 2),
                ]
            )

        household_avg_tax_rate = (
            (household_row.total_tax / household_row.gross_income_total) * 100
            if household_row.gross_income_total > 0
            else 0.0
        )
        row_values.extend(
            [
                _money(household_row.gross_income_total),
                _money(household_row.total_tax),
                round(household_avg_tax_rate, 2),
                _money(household_row.section7_expense_total),
                _money(household_row.net_income_total),
            ]
        )
        rows.append(row_values)

    return headers, rows


def write_projection_output(result: ProjectionResult, output_path: str | Path) -> Path:
    """Write the household projection rows to CSV or ODS based on the file extension."""
    path = Path(output_path)
    suffix = path.suffix.lower()
    path.parent.mkdir(parents=True, exist_ok=True)

    if suffix == ".csv":
        _write_projection_csv(result, path)
        cashflow_path = path.with_name(f"{path.stem}_cashflow.csv")
        _write_cashflow_csv(result, cashflow_path)
    elif suffix == ".ods":
        _write_projection_ods(result, path)
    else:
        raise ValueError("Projection output path must end with .csv or .ods")

    return path


def _write_projection_csv(result: ProjectionResult, output_path: Path) -> None:
    columns = _build_output_columns(result)

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow([column.header_row1 for column in columns])
        writer.writerow([column.header_row2 for column in columns])
        for row in result.household_rows:
            mapping = _projection_row_mapping(result, row, columns)
            writer.writerow([mapping[column.key] for column in columns])


def _write_cashflow_csv(result: ProjectionResult, output_path: Path) -> None:
    headers, rows = _cashflow_headers_and_rows(result)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)


def _build_ods_content_xml(result: ProjectionResult) -> str:
    columns = _build_output_columns(result)

    rows_xml = []
    for header_row in (
        [column.header_row1 for column in columns],
        [column.header_row2 for column in columns],
    ):
        header_cells = "".join(
            f'<table:table-cell office:value-type="string"><text:p>{escape(column)}</text:p></table:table-cell>'
            for column in header_row
        )
        rows_xml.append(f"<table:table-row>{header_cells}</table:table-row>")

    for row in result.household_rows:
        mapping = _projection_row_mapping(result, row, columns)
        cells = []
        for column in columns:
            value = mapping[column.key]
            if isinstance(value, int):
                cells.append(
                    f'<table:table-cell office:value-type="float" office:value="{value}"><text:p>{value}</text:p></table:table-cell>'
                )
            elif isinstance(value, float):
                cells.append(
                    f'<table:table-cell office:value-type="float" office:value="{value}"><text:p>{int(round(value))}</text:p></table:table-cell>'
                )
            else:
                cells.append(
                    f'<table:table-cell office:value-type="string"><text:p>{escape(str(value))}</text:p></table:table-cell>'
                )
        rows_xml.append(f"<table:table-row>{''.join(cells)}</table:table-row>")

    household_table_xml = (
        '<table:table table:name="Household Projection">'
        + "".join(rows_xml)
        + "</table:table>"
    )

    cashflow_headers, cashflow_rows = _cashflow_headers_and_rows(result)
    cashflow_rows_xml = []

    cashflow_header_cells = "".join(
        f'<table:table-cell office:value-type="string"><text:p>{escape(header)}</text:p></table:table-cell>'
        for header in cashflow_headers
    )
    cashflow_rows_xml.append(f"<table:table-row>{cashflow_header_cells}</table:table-row>")

    for row in cashflow_rows:
        cells = []
        for value in row:
            if isinstance(value, int):
                cells.append(
                    f'<table:table-cell office:value-type="float" office:value="{value}"><text:p>{value}</text:p></table:table-cell>'
                )
            elif isinstance(value, float):
                cells.append(
                    f'<table:table-cell office:value-type="float" office:value="{value}"><text:p>{value}</text:p></table:table-cell>'
                )
            else:
                cells.append(
                    f'<table:table-cell office:value-type="string"><text:p>{escape(str(value))}</text:p></table:table-cell>'
                )
        cashflow_rows_xml.append(f"<table:table-row>{''.join(cells)}</table:table-row>")

    cashflow_table_xml = (
        '<table:table table:name="CashFlow">'
        + "".join(cashflow_rows_xml)
        + "</table:table>"
    )

    return f'''<?xml version="1.0" encoding="UTF-8"?>
<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" office:version="1.3">
  <office:body>
    <office:spreadsheet>
            {household_table_xml}
            {cashflow_table_xml}
    </office:spreadsheet>
  </office:body>
</office:document-content>
'''


def _write_projection_ods(result: ProjectionResult, output_path: Path) -> None:
    content_xml = _build_ods_content_xml(result)
    styles_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<office:document-styles xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" office:version="1.3"></office:document-styles>
'''
    meta_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<office:document-meta xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" office:version="1.3"></office:document-meta>
'''
    manifest_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0">
  <manifest:file-entry manifest:full-path="/" manifest:media-type="application/vnd.oasis.opendocument.spreadsheet"/>
  <manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>
  <manifest:file-entry manifest:full-path="styles.xml" manifest:media-type="text/xml"/>
  <manifest:file-entry manifest:full-path="meta.xml" manifest:media-type="text/xml"/>
</manifest:manifest>
'''

    with ZipFile(output_path, mode="w") as archive:
        archive.writestr("mimetype", "application/vnd.oasis.opendocument.spreadsheet", compress_type=ZIP_STORED)
        archive.writestr("content.xml", content_xml, compress_type=ZIP_DEFLATED)
        archive.writestr("styles.xml", styles_xml, compress_type=ZIP_DEFLATED)
        archive.writestr("meta.xml", meta_xml, compress_type=ZIP_DEFLATED)
        archive.writestr("META-INF/manifest.xml", manifest_xml, compress_type=ZIP_DEFLATED)
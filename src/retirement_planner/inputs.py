"""Input loading for planner data files."""

from __future__ import annotations

from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    import tomli as tomllib

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
from retirement_planner.validator import validate_phase0_inputs


class InputFileError(ValueError):
    """Raised when input files are missing required fields or are malformed."""


def _require(mapping: dict[str, Any], field_name: str, context: str) -> Any:
    if field_name not in mapping:
        raise InputFileError(f"Missing required field '{field_name}' in {context}")
    return mapping[field_name]


def _parse_date(raw_value: str, field_name: str, context: str) -> date:
    try:
        return date.fromisoformat(raw_value)
    except ValueError as exc:
        raise InputFileError(
            f"Invalid ISO date for '{field_name}' in {context}: {raw_value}"
        ) from exc


def _load_toml_document(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise InputFileError(f"Input file does not exist: {path}")

    with path.open("rb") as handle:
        return tomllib.load(handle)


def _load_person(entry: dict[str, Any]) -> PersonProfile:
    context = f"people[{entry.get('name', '?')}]"
    overrides = {
        int(year): float(amount)
        for year, amount in entry.get("annual_salary_overrides", {}).items()
    }
    return PersonProfile(
        name=str(_require(entry, "name", context)),
        date_of_birth=_parse_date(
            str(_require(entry, "date_of_birth", context)),
            "date_of_birth",
            context,
        ),
        retirement_date=_parse_date(
            str(_require(entry, "retirement_date", context)),
            "retirement_date",
            context,
        ),
        salary_start=float(entry.get("salary_start", 0.0)),
        salary_growth_rate=float(entry.get("salary_growth_rate", 0.02)),
        annual_salary_overrides=overrides,
        cpp_start_age=int(entry.get("cpp_start_age", 70)),
        oas_start_age=int(entry.get("oas_start_age", 65)),
        cpp_percent_of_max=float(entry.get("cpp_percent_of_max", 1.0)),
        oas_percent_of_max=float(entry.get("oas_percent_of_max", 1.0)),
    )


def _load_account(entry: dict[str, Any]) -> AccountBalance:
    context = f"accounts[{entry.get('owner_name', '?')}]"
    account_type = str(_require(entry, "account_type", context))
    try:
        normalized_type = AccountType(account_type)
    except ValueError as exc:
        valid_values = ", ".join(member.value for member in AccountType)
        raise InputFileError(
            f"Invalid account_type '{account_type}' in {context}. Expected one of: {valid_values}"
        ) from exc

    return AccountBalance(
        owner_name=str(_require(entry, "owner_name", context)),
        account_type=normalized_type,
        balance=float(_require(entry, "balance", context)),
    )


def _load_pension(entry: dict[str, Any]) -> DefinedBenefitPension:
    context = f"pensions[{entry.get('owner_name', '?')}]"
    return DefinedBenefitPension(
        owner_name=str(_require(entry, "owner_name", context)),
        provider_name=str(_require(entry, "provider_name", context)),
        start_date=_parse_date(
            str(_require(entry, "start_date", context)),
            "start_date",
            context,
        ),
        monthly_lifetime_amount=float(_require(entry, "monthly_lifetime_amount", context)),
        monthly_bridge_amount=float(entry.get("monthly_bridge_amount", 0.0)),
        bridge_end_age=(
            int(entry["bridge_end_age"]) if entry.get("bridge_end_age") is not None else None
        ),
        enrolment_date=(
            _parse_date(str(entry["enrolment_date"]), "enrolment_date", context)
            if entry.get("enrolment_date")
            else None
        ),
        contributory_service_years=(
            float(entry["contributory_service_years"])
            if entry.get("contributory_service_years") is not None
            else None
        ),
        eligibility_service_years=(
            float(entry["eligibility_service_years"])
            if entry.get("eligibility_service_years") is not None
            else None
        ),
    )


def _load_section7(entry: dict[str, Any]) -> Section7Obligation:
    context = "section7_obligation"
    return Section7Obligation(
        payer_name=str(_require(entry, "payer_name", context)),
        payer_gross_income=float(_require(entry, "payer_gross_income", context)),
        other_party_gross_income=float(_require(entry, "other_party_gross_income", context)),
        annual_expense=float(_require(entry, "annual_expense", context)),
        indexed_to_inflation=bool(entry.get("indexed_to_inflation", True)),
    )


def _load_residence(entry: dict[str, Any]) -> Residence:
    context = "residence"
    return Residence(
        description=str(_require(entry, "description", context)),
        current_value=float(_require(entry, "current_value", context)),
        annual_growth_rate=(
            float(entry["annual_growth_rate"])
            if entry.get("annual_growth_rate") is not None
            else None
        ),
    )


def _load_config(document: dict[str, Any], default_data_dir: Path) -> PlannerConfig:
    config_entry = document.get("config", {})
    assumptions_entry = document.get("assumptions", {})
    assumptions = EconomicAssumptions(
        inflation_rate=float(assumptions_entry.get("inflation_rate", 0.02)),
        investment_return_rate=float(assumptions_entry.get("investment_return_rate", 0.05)),
        salary_growth_rate=float(assumptions_entry.get("salary_growth_rate", 0.02)),
        house_growth_rate=float(assumptions_entry.get("house_growth_rate", 0.02)),
    )

    run_date_raw = config_entry.get("run_date")
    run_date = date.today() if run_date_raw is None else _parse_date(str(run_date_raw), "run_date", "config")

    return PlannerConfig(
        start_year=int(config_entry.get("start_year", 2026)),
        end_year=int(config_entry.get("end_year", 2077)),
        run_date=run_date,
        assumptions=assumptions,
        data_dir=Path(str(config_entry.get("data_dir", default_data_dir))),
    )


def _resolve_manifest_file_paths(manifest_path: Path, manifest: dict[str, Any]) -> dict[str, Path]:
    data_entry = manifest.get("data", {})
    files_entry = manifest.get("files", {})

    base_dir_value = str(_require(data_entry, "base_dir", "data"))
    base_dir = (manifest_path.parent / base_dir_value).resolve(strict=False)

    people_file = str(_require(files_entry, "people", "files"))
    config_file = str(files_entry.get("config", "config.toml"))

    return {
        "base_dir": base_dir,
        "config": base_dir / config_file,
        "people": base_dir / people_file,
        "accounts": base_dir / str(files_entry.get("accounts", "accounts.toml")),
        "pensions": base_dir / str(files_entry.get("pensions", "pensions.toml")),
        "section7": base_dir / str(files_entry.get("section7", "section7.toml")),
        "residence": base_dir / str(files_entry.get("residence", "residence.toml")),
    }


def load_plan_from_toml(
    file_path: str | Path,
    project_root: Path | None = None,
) -> tuple[PlannerConfig, HouseholdPlan]:
    """Load planner configuration and household data from a manifest TOML file."""
    path = Path(file_path)

    manifest = _load_toml_document(path)
    file_paths = _resolve_manifest_file_paths(path, manifest)
    config_document = _load_toml_document(file_paths["config"]) if file_paths["config"].exists() else {}
    people_document = _load_toml_document(file_paths["people"])
    accounts_document = _load_toml_document(file_paths["accounts"]) if file_paths["accounts"].exists() else {}
    pensions_document = _load_toml_document(file_paths["pensions"]) if file_paths["pensions"].exists() else {}
    section7_document = _load_toml_document(file_paths["section7"]) if file_paths["section7"].exists() else {}
    residence_document = _load_toml_document(file_paths["residence"]) if file_paths["residence"].exists() else {}

    people_entries = people_document.get("people", [])
    if not people_entries:
        raise InputFileError("At least one [[people]] entry is required")

    household = HouseholdPlan(
        people=[_load_person(entry) for entry in people_entries],
        accounts=[_load_account(entry) for entry in accounts_document.get("accounts", [])],
        pensions=[_load_pension(entry) for entry in pensions_document.get("pensions", [])],
        section7_obligation=(
            _load_section7(section7_document["section7_obligation"])
            if section7_document.get("section7_obligation")
            else None
        ),
        residence=(
            _load_residence(residence_document["residence"])
            if residence_document.get("residence")
            else None
        ),
    )
    config = _load_config(config_document, default_data_dir=file_paths["base_dir"])
    root = project_root or path.parent.parent
    validate_phase0_inputs(household=household, config=config, project_root=root)
    return config, household


def summarize_loaded_plan(config: PlannerConfig, household: HouseholdPlan) -> dict[str, Any]:
    """Build a compact summary for CLI preview output."""
    return {
        "start_year": config.start_year,
        "end_year": config.end_year,
        "data_dir": str(config.data_dir),
        "people": [person.name for person in household.people],
        "account_count": len(household.accounts),
        "pension_count": len(household.pensions),
        "has_section7_obligation": household.section7_obligation is not None,
        "has_residence": household.residence is not None,
        "assumptions": asdict(config.assumptions),
    }

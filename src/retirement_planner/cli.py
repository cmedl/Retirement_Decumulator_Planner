"""Command line entry point for the retirement planner."""

import argparse
from pathlib import Path
import sys

from retirement_planner.inputs import InputFileError, load_plan_from_toml, summarize_loaded_plan
from retirement_planner.projection import project_household, projection_header_summary, write_projection_output
from retirement_planner.planner import estimate_years_until_depletion
from retirement_planner.validator import ValidationError


def main() -> None:
    """Run a default example calculation or preview a plan input file."""
    parser = argparse.ArgumentParser(prog="retirement-planner")
    subparsers = parser.add_subparsers(dest="command")

    preview_parser = subparsers.add_parser("preview")
    preview_parser.add_argument("plan_path", type=Path)

    project_parser = subparsers.add_parser("project")
    project_parser.add_argument("plan_path", type=Path)
    project_parser.add_argument("output_path", type=Path)

    args = parser.parse_args(sys.argv[1:])

    if args.command == "preview":
        _preview_plan(args.plan_path)
        return

    if args.command == "project":
        _project_plan(args.plan_path, args.output_path)
        return

    years = estimate_years_until_depletion(
        starting_balance=1_000_000,
        annual_withdrawal=50_000,
        annual_return_rate=0.04,
    )
    print(f"Estimated years until depletion: {years}")


def _preview_plan(plan_path: Path) -> None:
    """Load and print a compact summary of an input file."""
    try:
        config, household = load_plan_from_toml(plan_path, project_root=Path.cwd())
    except (InputFileError, ValidationError) as exc:
        print(f"Input error: {exc}")
        raise SystemExit(1) from exc

    summary = summarize_loaded_plan(config, household)
    print("Plan preview")
    for key, value in summary.items():
        print(f"{key}: {value}")


def _project_plan(plan_path: Path, output_path: Path) -> None:
    """Load inputs and write a deterministic Phase 1B projection file."""
    try:
        config, household = load_plan_from_toml(plan_path, project_root=Path.cwd())
    except (InputFileError, ValidationError) as exc:
        print(f"Input error: {exc}")
        raise SystemExit(1) from exc

    result = project_household(household, config)
    written_path = write_projection_output(result, output_path)
    print("Phase 1B projection written")
    print(projection_header_summary())
    print(f"output: {written_path}")


if __name__ == "__main__":
    main()

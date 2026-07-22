"""Command line entry point for the retirement planner."""

from pathlib import Path
import sys

from retirement_planner.inputs import InputFileError, load_plan_from_toml, summarize_loaded_plan
from retirement_planner.planner import estimate_years_until_depletion


def main() -> None:
    """Run a default example calculation or preview a plan input file."""
    args = sys.argv[1:]
    if len(args) == 2 and args[0] == "preview":
        _preview_plan(Path(args[1]))
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
    except InputFileError as exc:
        print(f"Input error: {exc}")
        raise SystemExit(1) from exc

    summary = summarize_loaded_plan(config, household)
    print("Plan preview")
    for key, value in summary.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()

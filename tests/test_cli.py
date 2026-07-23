from pathlib import Path
import os
import subprocess
import sys


def test_cli_preview_outputs_summary(tmp_path: Path) -> None:
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
    (data_dir / "people.toml").write_text(
        """
[[people]]
name = "Chris"
date_of_birth = "1980-05-01"
retirement_date = "2040-07-01"
""".strip(),
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, "-m", "retirement_planner.cli", "preview", str(input_file)],
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "PYTHONPATH": "src"},
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Plan preview" in result.stdout
    assert "people: ['Chris']" in result.stdout


def test_cli_project_outputs_projection_table(tmp_path: Path) -> None:
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
""".strip(),
        encoding="utf-8",
    )
    (data_dir / "config.toml").write_text(
        """
[config]
start_year = 2026
end_year = 2027

[assumptions]
inflation_rate = 0.02
investment_return_rate = 0.05
salary_growth_rate = 0.02
house_growth_rate = 0.02
""".strip(),
        encoding="utf-8",
    )
    (data_dir / "people.toml").write_text(
        """
[[people]]
name = "Chris"
date_of_birth = "1980-05-01"
retirement_date = "2040-07-01"
salary_start = 100000
""".strip(),
        encoding="utf-8",
    )
    (data_dir / "accounts.toml").write_text(
        """
[[accounts]]
owner_name = "Chris"
account_type = "rrsp"
balance = 1000
""".strip(),
        encoding="utf-8",
    )

    output_file = tmp_path / "projection.csv"

    result = subprocess.run(
        [sys.executable, "-m", "retirement_planner.cli", "project", str(input_file), str(output_file)],
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "PYTHONPATH": "src"},
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Phase 1B projection written" in result.stdout
    assert output_file.exists()
    assert "Capital Assets" in output_file.read_text(encoding="utf-8")

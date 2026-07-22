"""Application configuration models."""

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from retirement_planner.models import EconomicAssumptions


@dataclass(slots=True)
class PlannerConfig:
    """Top-level planner runtime configuration."""

    start_year: int = 2026
    end_year: int = 2077
    run_date: date = field(default_factory=date.today)
    assumptions: EconomicAssumptions = field(default_factory=EconomicAssumptions)
    data_dir: Path = Path("data")

    def resolve_data_dir(self, project_root: Path | None = None) -> Path:
        """Resolve configured data directory, preserving symlink compatibility."""
        root = project_root or Path.cwd()
        configured = self.data_dir.expanduser()
        if configured.is_absolute():
            return configured.resolve(strict=False)
        return (root / configured).resolve(strict=False)

    def ensure_data_dir(self, project_root: Path | None = None) -> Path:
        """Ensure resolved data directory exists and is usable."""
        resolved = self.resolve_data_dir(project_root=project_root)
        if resolved.exists() and not resolved.is_dir():
            raise ValueError(f"Configured data_dir is not a directory: {resolved}")
        resolved.mkdir(parents=True, exist_ok=True)
        return resolved

#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

. .venv/bin/activate
python -m pip install -e .
python -m pip install pytest
PYTHONPATH=src python -m pytest -q
mkdir -p build
PYTHONPATH=src python -m retirement_planner.cli project data/master_data.toml build/projection.csv
echo "Demo output written to build/projection.csv"
# Retirement Decumulator Planner

A starter Python project for modeling retirement decumulation scenarios.

## Quick start

1. Create a virtual environment.
2. Install in editable mode:

```bash
pip install -e .
```

3. Run the CLI:

```bash
retirement-planner
```

4. Run tests:

```bash
pytest
```

## Build / Test / Demo

Run the one-command workflow script:

```bash
./scripts/build_test_demo.sh
```

To run the projection command directly, provide an output file ending in `.csv` or `.ods`:

```bash
PYTHONPATH=src python -m retirement_planner.cli project data/master_data.toml build/projection.csv
```

# Data Storage Convention (Phase 0 Contract)

## Objective

Keep user planning data separate from model code and allow backup-friendly storage via symlinks.

## Default Directory

1. The planner uses a configurable data path with default value data/ at the project root.
2. This data path is intended for user inputs, scenario files, generated outputs, and local run artifacts.

## Git Behavior

1. The data directory is gitignored so personal planning data is not committed.
2. The only tracked top-level file in data/ is master_data.toml.
3. The actual data files live under the manifest-declared subdirectory and remain gitignored.

## Manifest Layout

1. data/master_data.toml is the entrypoint file.
2. master_data.toml declares the base data directory and the filenames to load.
3. The base data directory can be a normal directory or a symlink to a backup-managed location.
4. The manifest points to separate TOML files for config, people, accounts, pensions, section 7, and residence data.

## Symlink Support

1. The configured data path may be a normal directory or a symlink to another directory.
2. This allows the data location to point to a backup-managed location.
3. The application resolves and validates the configured path at runtime.

## Configuration Rule

1. Data path is externalized in planner configuration and must not be hard-coded inside model logic.

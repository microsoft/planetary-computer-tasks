# Project Guidelines — Planetary Computer Tasks (pctasks)

## Architecture

Monorepo of 12 Python namespace packages under `pctasks/`, each independently installable via `hatchling`. Dependency order: `core → cli → task → client → ingest → ingest_task → dataset → run → notify → router → server → dev`. Additional code in `pctasks_funcs/` (Azure Functions), `datasets/` (~60 dataset definitions), and `deployment/` (Terraform/Helm).

**Core data flow**: blob storage assets → splits (by prefix) → chunks (file listing CSVs) → `Collection.create_item()` produces pystac Items → ingest into PgSTAC via pypgstac.

Key abstractions:
- **`PCBaseModel`** (`pctasks/core/pctasks/core/models/base.py`): Pydantic v2 base with YAML serde, `by_alias=True`, `exclude_none=True`.
- **`Task[T, U]`** (`pctasks/task/pctasks/task/task.py`): Generic abstract task, define `_input_model`/`_output_model` and `run(input, context)`.
- **`Collection`** (`pctasks/dataset/pctasks/dataset/collection.py`): Abstract base for datasets; implement `create_item(cls, asset_uri, storage_factory) -> List[pystac.Item] | WaitTaskResult` as a classmethod.
- **`StorageFactory`**: Creates `Storage` objects from `blob://<account>/<container>/<path>` URIs.
- **Settings**: `pydantic-settings` with double-underscore env vars (`PCTASKS__COSMOSDB__URL`, `PCTASKS_RUN__TASK_RUNNER_TYPE`).

## Code Style

- **Formatter**: black (default settings) + isort. Run `scripts/format`.
- **Linter**: flake8 with `max-line-length = 120`, ignores `E203, W503, E731, E722` (see `.flake8`).
- **Type checking**: mypy with `disallow_untyped_defs = True` — all functions must have type annotations (see `mypy.ini`).
- **No docstrings** unless explicitly requested.
- All models extend `PCBaseModel` (Pydantic v2). Use `model_validate`, `model_dump`, `field_validator`, `model_validator`.

## Build and Test

```bash
scripts/install              # Create venv with uv, install all packages in editable mode
scripts/server               # Start local dev stack (Azurite, PgSTAC, server, STAC API)
scripts/test                 # Full lint + test suite (runs in Docker via docker-compose.console.yml)
scripts/test --subpackage core   # Test one package
scripts/test --test-only     # Skip lint
scripts/test --lint-only     # Skip tests
scripts/format               # Auto-format all packages (black + isort)
```

Per-package test commands (from within `pctasks/<pkg>/`):
```bash
pytest tests/                        # Run package tests
mypy --config-file ../../mypy.ini pctasks   # Type-check
```

## Project Conventions

### Dataset directory pattern (`datasets/<name>/`)
```
dataset.yaml            # Required: dataset definition (id, image, collections, asset_storage, chunks)
<name>.py               # Required: Collection subclass with create_item classmethod
collection/template.json  # STAC collection Jinja2 template
test_<name>.py          # Tests: import collection class, call create_item with blob URIs
requirements.txt        # Optional: extra pip deps
Dockerfile              # Optional: custom image (otherwise uses pctasks-task-base)
```

Dataset YAML references code via `${{ local.path(./<file>.py) }}` and class via `<module>:<ClassName>` (no `.py`).

### Templating syntax in YAML
- `${{ args.<name> }}` — CLI arguments
- `${{ secrets.<key> }}` — KeyVault/dev-secrets.yaml
- `${{ local.path(<relative>) }}` — Path relative to YAML file
- `${{ local.file(<relative>) }}` — Inline file contents

### CLI
Click-based with plugin discovery via `pctasks.commands` entry point group. Each package registers subcommands in its `pyproject.toml`.

### Testing patterns
- pytest with `asyncio_mode = auto` (see `pytest.ini`)
- Dataset tests are co-located: `datasets/<name>/test_<name>.py`
- Package tests: `pctasks/<pkg>/tests/`
- Integration tests: `tests/`
- Use `StorageFactory()` in tests for blob access; `SimpleWorkflowExecutor` for local workflow execution.

## Integration Points

- **Azure Blob Storage**: All asset URIs use `blob://<account>/<container>/<path>` scheme.
- **Cosmos DB**: Workflow/run state persistence; emulated locally via docker-compose.
- **PgSTAC**: STAC item storage (PostgreSQL + PostGIS), port 5499 locally.
- **Azurite**: Local Azure Storage emulator, ports 10000-10002.
- **Argo Workflows**: Production workflow orchestration on Kubernetes.
- **Azure Batch**: Production task execution.
- **Kind cluster**: Local Kubernetes for Argo testing (`scripts/cluster setup`).

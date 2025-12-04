# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is PCTasks?

PCTasks is a scalable workflow orchestration system built on Azure and Kubernetes. It's the reactive ETL system that powers the Microsoft Planetary Computer STAC catalog, managing dataset ingestion, processing, and updates.

**Core Concept**: PCTasks takes dataset configurations (`dataset.yaml`), generates workflows, and executes them as containerized tasks on Kubernetes (via Argo Workflows) or Azure Batch.

## Architecture Overview

### Multi-Package Monorepo Structure

This is a Python monorepo with 12 distinct packages under `pctasks/`:

```
pctasks/
├── core/          # Base models, storage, templating, shared utilities
├── cli/           # Top-level CLI entry point
├── client/        # Client library for API interaction, profile management
├── server/        # FastAPI server exposing REST API
├── task/          # Task execution runtime (runs inside containers)
├── run/           # Workflow/task runners (Argo, Batch, local)
├── dataset/       # Dataset model and processing logic
├── ingest/        # Ingest workflow generation
├── ingest_task/   # Ingest task implementations (PgSTAC database operations)
├── router/        # Message routing between queues
├── notify/        # Notification handling
└── dev/           # Development utilities (setup, testing)
```

Each package has its own `pyproject.toml` and can be installed independently, but they depend on each other (e.g., most depend on `pctasks.core`).

### Request Flow

1. **Client** → API Server (FastAPI)
2. **Server** → CosmosDB (workflow definitions) + Azure Queues (submission)
3. **Router** (Azure Function) → Reads queue, creates Argo Workflow
4. **Argo** → Schedules tasks as Kubernetes Pods
5. **Task Container** → Executes `pctasks.task` runtime
6. **Task** → Reads from Blob Storage, processes data, writes to PgSTAC
7. **Notifications** → Item updates sent to queue for downstream consumers

### Key Subsystems

- **Templating**: Jinja2-like syntax (`${{ ... }}`) for dynamic values in workflow/dataset configs
  - `${{ secrets.* }}`: KeyVault secrets
  - `${{ args.* }}`: Workflow arguments
  - `${{ local.path(...) }}`: Local file references
  - `${{ pc.get_token(...) }}`: SAS token generation

- **Storage Abstraction**: `StorageFactory` provides unified access to Azure Blob Storage with automatic SAS token handling

- **Chunking**: Large datasets split into "chunk files" (lists of asset URIs) for parallel processing

- **Code Injection**: Custom Python code/requirements uploaded to Blob Storage, downloaded at task runtime

## Development Commands

### Initial Setup

```bash
# One-time setup: creates dev environment with Azurite, CosmosDB emulator, Kubernetes (kind)
scripts/setup

# Drop into development container
scripts/console
```

Inside the dev container, the `pctasks` CLI is available with access to local services.

### Testing

```bash
# Run all tests (lint + unit tests)
scripts/test

# Test specific package
scripts/test --subpackage core

# Only run tests, skip linting
scripts/test --test-only

# Only lint
scripts/test --lint-only

# Run integration tests (requires cluster running)
scripts/test-integration
```

**Test Location**: Each package has a `tests/` directory (e.g., `pctasks/core/tests/`).

**Linters Used**: mypy, black, isort, flake8

### Code Formatting

```bash
# Auto-format all code
scripts/format
```

Runs black and isort on all packages.

### Local Development Workflow

```bash
# Start local servers (API, Argo, etc.)
scripts/server

# Or start in background
scripts/server --detached

# Install packages in editable mode after code changes
scripts/install
```

### Building and Publishing Images

```bash
# Build all Docker images locally
scripts/build

# Publish images to ACR (requires authentication)
scripts/publish --acr <registry> --tag <tag>
```

**Core Images**:
- `pctasks-task-base`: Base image with all pctasks packages
- `pctasks-ingest`: Ingest-specific image
- `pctasks-server`: API server image
- `pctasks-run`: Workflow runner image

**Dataset Images**: Built manually per dataset (e.g., `pctasks-aster`):
```bash
az acr build -r <registry> --subscription <sub> \
    -t pctasks-aster:latest \
    -f datasets/aster/Dockerfile .
```

### Profile Management

PCTasks uses profiles to target different environments (dev, staging, production):

```bash
# Create new profile
pctasks profile create staging

# Set default profile
pctasks profile set staging

# Use specific profile
pctasks -p staging <command>

# Or via environment variable
export PCTASKS_PROFILE=staging
```

Profiles stored in `~/.pctasks/<profile>.yaml`.

## Working with Datasets

### Dataset Configuration (`dataset.yaml`)

Each dataset in `datasets/` has a `dataset.yaml` that defines:
- **image**: Docker image to use for tasks
- **code**: Custom Python modules/requirements to inject
- **collections**: STAC Collections with asset/chunk storage locations
- **environment**: Environment variables (e.g., Azure credentials)

### Common Dataset Commands

```bash
# Ingest collection metadata to database
pctasks dataset ingest-collection -d datasets/aster/dataset.yaml --submit

# Process items (ETL workflow)
pctasks dataset process-items -d datasets/aster/dataset.yaml --limit 10 --submit

# Generate chunks (asset inventory)
pctasks dataset create-chunks -d datasets/aster/dataset.yaml --submit

# Target staging environment
pctasks dataset process-items -d dataset.yaml --target staging --submit
```

### Ingest Commands (Direct Collection/NDJSON Ingest)

```bash
# Ingest collection
pctasks ingest collection ./collection/ --target staging --submit

# Ingest NDJSON items
pctasks ingest ndjsons <collection-id> blob://account/container/path/ \
    --target staging \
    --num-workers 8 \
    --submit
```

### Workflow Management

```bash
# Submit workflow from YAML file
pctasks workflow upsert-and-submit workflow.yaml

# List workflows
pctasks workflow list

# Get workflow details
pctasks workflow get <workflow-id>

# Submit existing workflow with arguments
pctasks workflow submit <workflow-id> --arg since 2024-01-01
```

### Creating a New Dataset

See `docs/getting_started/creating_a_dataset.md` for full guide. Quick checklist:

1. Create `datasets/<name>/dataset.yaml`
2. Create collection template in `datasets/<name>/collection/`
3. Implement `Collection` subclass (or use `PremadeItemCollection`)
4. Add `requirements.txt` if using custom packages
5. Test with `--limit` flag first
6. Optionally build custom Docker image if dependencies are heavy

## Important Configuration Files

- `scripts/env`: Defines `PACKAGE_DIRS` array and helper functions used by scripts
- `docker-compose.console.yml`: Dev container configuration
- `dev-secrets.yaml`: Local secrets (created from `dev-secrets.template.yaml`)
- `deployment/terraform/`: Infrastructure as Code for Azure resources
- `.github/workflows/cicd.yml`: CI/CD pipeline

## Common Patterns

### Using Custom Code with `pctasks-task-base`

Instead of building a custom Docker image, you can inject code at runtime:

```yaml
# dataset.yaml
image: ${{ args.registry }}/pctasks-task-base:latest
code:
  src: ${{ local.path(./my_module.py) }}
  requirements: ${{ local.path(./requirements.txt) }}
```

Code is uploaded to Blob Storage, downloaded, and installed before task execution.

### Collection Implementation

```python
from pctasks.dataset.collection import Collection

class MyCollection(Collection):
    @classmethod
    def create_item(cls, asset_uri: str, storage_factory: StorageFactory):
        # Return a pystac.Item or list of Items
        return [item]
```

### Accessing Secrets in Workflows

```yaml
environment:
  DB_CONNECTION_STRING: ${{ secrets.pgstac-connection-string }}
```

Secrets retrieved from Azure KeyVault at runtime.

## Running a Single Test

```bash
# Enter dev container
scripts/console

# Run specific test file
pytest pctasks/core/tests/test_storage.py

# Run specific test function
pytest pctasks/core/tests/test_storage.py::test_blob_storage

# Run with verbose output
pytest -vv pctasks/core/tests/test_storage.py
```

## Deployment

Deployment is handled via Terraform and Helm:

```bash
# Enter deployment container
scripts/console --deploy

# Deploy to dev stack
bin/deploy -t terraform/dev

# Staging/production deployed via CI/CD only
```

**Environments**:
- `dev`: Local kind cluster, personal development
- `staging`: Deployed to "Planetary Computer Test" subscription via CI/CD
- `production`: Deployed to production subscription via CI/CD

## Troubleshooting

### Local Development

- **Azurite not responding**: Run `scripts/setup --azurite`
- **CosmosDB emulator issues**: Run `scripts/setup --reset-cosmos`
- **Clear test data**: Run `scripts/setup --clear-records`
- **Services not running**: Check `docker compose ps` or restart with `scripts/server`

### Task Execution

- **Import errors**: Ensure code is in `code.src` or requirements are in `code.requirements`
- **Storage access denied**: Check SAS tokens in `asset_storage.token` or service principal credentials
- **Task timeout**: Increase timeout in task definition or batch pool settings

### Workflow Issues

- **Workflow won't submit**: Validate YAML syntax and required fields (workflow_id, dataset, jobs)
- **Template errors**: Check `${{ }}` syntax and available template variables
- **Missing secrets**: Ensure secrets exist in KeyVault and are referenced correctly

## Documentation

Full documentation: https://planetary-computer-tasks.readthedocs.io

Key docs to reference:
- `docs/getting_started/creating_a_dataset.md`: Dataset creation guide
- `docs/user_guide/templating.md`: Template syntax reference
- `docs/user_guide/chunking.md`: Chunking system explanation
- `docs/development/deploying.md`: Deployment guide

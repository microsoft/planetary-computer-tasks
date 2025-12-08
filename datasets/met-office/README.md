# Met Office Dataset

This directory contains the configuration and scripts for ingesting Met Office weather forecast data into the Planetary Computer.

## Collections

This dataset includes eight collections:

### Global Collections (10km resolution)

- **met-office-global-deterministic-height** - Weather parameters at specific atmospheric height levels
- **met-office-global-deterministic-near-surface** - Near-surface weather parameters (precipitation, temperature, wind, etc.)
- **met-office-global-deterministic-pressure** - Weather parameters at specific atmospheric pressure levels
- **met-office-global-deterministic-whole-atmosphere** - Whole atmosphere parameters (CAPE, cloud amounts, etc.)

### UK Collections (2km resolution)

- **met-office-uk-deterministic-height** - Weather parameters at specific atmospheric height levels
- **met-office-uk-deterministic-near-surface** - Near-surface weather parameters
- **met-office-uk-deterministic-pressure** - Weather parameters at specific atmospheric pressure levels
- **met-office-uk-deterministic-whole-atmosphere** - Whole atmosphere parameters

## Scripts

The `scripts/` directory contains shell scripts for managing the dataset workflow:

- **`ingest-collections.sh`** - Ingest all eight Met Office collections into the STAC catalog:

  ```bash
  ./scripts/ingest-collections.sh
  ```

- **`upload-all.sh`** - Process items for all collections using a specified chunkset id:

  ```bash
  ./scripts/upload-all.sh <chunkset-id>
  ```

- **`process-items-and-monitor.sh`** - Process items for a specific collection and monitor the workflow progress:

  ```bash
  ./scripts/process-items-and-monitor.sh <chunkset-id> <collection-id>
  ```

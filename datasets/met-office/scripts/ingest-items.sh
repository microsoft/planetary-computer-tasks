#!/usr/bin/env sh

set -e

COLLECTION_TYPE="${1:-all}"

case "$COLLECTION_TYPE" in
  global)
    COLLECTIONS="
      met-office-global-deterministic-height
      met-office-global-deterministic-near-surface
      met-office-global-deterministic-pressure
      met-office-global-deterministic-whole-atmosphere
    "
    ;;
  uk)
    COLLECTIONS="
      met-office-uk-deterministic-height
      met-office-uk-deterministic-near-surface
      met-office-uk-deterministic-pressure
      met-office-uk-deterministic-whole-atmosphere
    "
    ;;
  all)
    COLLECTIONS="
      met-office-global-deterministic-height
      met-office-global-deterministic-near-surface
      met-office-global-deterministic-pressure
      met-office-global-deterministic-whole-atmosphere
      met-office-uk-deterministic-height
      met-office-uk-deterministic-near-surface
      met-office-uk-deterministic-pressure
      met-office-uk-deterministic-whole-atmosphere
    "
    ;;
  *)
    echo "Usage: $0 [global|uk|all]"
    echo "  global - Ingest only global collections"
    echo "  uk     - Ingest only UK collections"
    echo "  all    - Ingest all collections (default)"
    exit 1
    ;;
esac

for collection in $COLLECTIONS
do
  pctasks dataset process-items \
    -d dataset.yaml \
    -a registry pccomponents.azurecr.io \
    -c "$collection" ingest \
    --since '2026-01-01T00:00:00Z' \
    --limit 100 \
    --confirm --submit
done

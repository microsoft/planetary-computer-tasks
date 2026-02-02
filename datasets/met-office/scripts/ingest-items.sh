#!/usr/bin/env sh

set -e

COLLECTION_TYPE="all"
SINCE=""

usage() {
  echo "Usage: $0 [--collection global|uk|all] [--since datetime]"
  echo "  --collection  - Collection type: global, uk, or all (default: all)"
  echo "  --since       - Optional datetime to filter items (e.g., 2024-01-01)"
  exit 1
}

while [ $# -gt 0 ]; do
  case "$1" in
    --collection)
      COLLECTION_TYPE="$2"
      shift 2
      ;;
    --since)
      SINCE="$2"
      shift 2
      ;;
    -h|--help)
      usage
      ;;
    *)
      echo "Unknown option: $1"
      usage
      ;;
  esac
done

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
    echo "Invalid collection type: $COLLECTION_TYPE"
    usage
    ;;
esac

SINCE_ARG=""
SUBMIT_MODE="--upsert"
if [ -n "$SINCE" ]; then
  SINCE_ARG="-a since $SINCE"
  SUBMIT_MODE="--submit"
fi

for collection in $COLLECTIONS
do
  pctasks dataset process-items \
    -d dataset.yaml \
    -a registry pccomponents.azurecr.io \
    --is-update-workflow \
    --workflow-id $collection-update \
    -c "$collection" ingest \
    --confirm $SUBMIT_MODE $SINCE_ARG -a year-prefix 2026
done

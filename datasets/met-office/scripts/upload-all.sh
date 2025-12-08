#!/bin/bash

set -e

if [ $# -ne 1 ]; then
    echo "Usage: $0 <chunkset-id>"
    echo "Example: $0 my-chunkset"
    exit 1
fi

CHUNKSET_ID="$1"

echo "Processing items for all Met Office collections"
echo "Chunkset ID: ${CHUNKSET_ID}"
echo ""

COLLECTIONS=(
  "met-office-global-deterministic-height"
  "met-office-global-deterministic-near-surface"
  "met-office-global-deterministic-pressure"
  "met-office-global-deterministic-whole-atmosphere"
  "met-office-uk-deterministic-height"
  "met-office-uk-deterministic-near-surface"
  "met-office-uk-deterministic-pressure"
  "met-office-uk-deterministic-whole-atmosphere"
)

for COLLECTION_ID in "${COLLECTIONS[@]}"; do
  echo "========================================"
  echo "Processing collection: ${COLLECTION_ID}"
  echo "========================================"

  pctasks dataset process-items "${CHUNKSET_ID}" \
    -d dataset.yaml \
    -c "${COLLECTION_ID}" \
    --submit \
    -a registry pccomponents.azurecr.io

  echo ""
  echo "Submitted workflow for ${COLLECTION_ID}"
  echo ""
done

echo "========================================"
echo "All collections submitted successfully!"
echo "========================================"

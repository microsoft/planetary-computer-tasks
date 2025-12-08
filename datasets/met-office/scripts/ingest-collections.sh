#!/bin/bash

set -e

echo "Ingesting all Met Office collections"
echo ""

for collection in \
  met-office-global-deterministic-height \
  met-office-global-deterministic-near-surface \
  met-office-global-deterministic-pressure \
  met-office-global-deterministic-whole-atmosphere \
  met-office-uk-deterministic-height \
  met-office-uk-deterministic-near-surface \
  met-office-uk-deterministic-pressure \
  met-office-uk-deterministic-whole-atmosphere
do
  echo "========================================"
  echo "Ingesting collection: ${collection}"
  echo "========================================"

  pctasks dataset ingest-collection \
    -d datasets/met-office/dataset.yaml \
    -a registry pccomponents \
    -c "$collection" \
    --submit

  echo ""
  echo "Submitted ingest for ${collection}"
  echo ""
done

echo "========================================"
echo "All collections submitted successfully!"
echo "========================================"

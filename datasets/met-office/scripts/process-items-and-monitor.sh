#!/bin/bash

set -e

if [ $# -ne 2 ]; then
    echo "Usage: $0 <chunkset-id> <collection-id>"
    echo "Example: $0 my-chunkset met-office-global-deterministic-height"
    exit 1
fi

CHUNKSET_ID="$1"
COLLECTION_ID="$2"

echo "Creating chunks for collection: ${COLLECTION_ID}"
echo "Chunkset ID: ${CHUNKSET_ID}"

# Run create-chunks and capture output to a temp file while still showing it
TEMP_FILE=$(mktemp)
trap "rm -f ${TEMP_FILE}" EXIT

pctasks dataset process-items "${CHUNKSET_ID}" \
    -d dataset.yaml \
    -c "${COLLECTION_ID}" \
    --submit \
    -a registry pccomponents.azurecr.io | tee "${TEMP_FILE}"

# Extract the run ID from the captured output
RUN_ID=$(grep -oE '[a-f0-9-]{36}' "${TEMP_FILE}" | tail -1)

if [ -z "${RUN_ID}" ]; then
    echo "Error: Could not extract run ID from output"
    exit 1
fi

echo ""
echo "Monitoring run: ${RUN_ID}"
echo ""

# Monitor the run status
if ! pctasks runs status -w "${RUN_ID}"; then
    echo ""
    echo "Status command failed. Fetching run log..."
    echo ""
    pctasks runs get run-log "${RUN_ID}"
    exit 1
fi

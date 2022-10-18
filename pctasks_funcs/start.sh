#!/bin/bash

# Install the CosmosDB Emulator certificate
FETCH="YES"
FETCHES=0
MAX_FETCHES=10

if [ "${COSMOSDB_EMULATOR_HOST}" ] && [[ "${PCTASKS_COSMOSDB__URL}" == *"${COSMOSDB_EMULATOR_HOST}"* ]]; then
    # Wait some time before hitting the cosmosdb container
    sleep 15

    while [ "$FETCH" == "YES" ]; do
        echo "Fetching CosmosDB Emulator certificate..."
        curl -f -k "${PCTASKS_COSMOSDB__URL}_explorer/emulator.pem" >~/emulatorcert.crt
        if [ $? -ne 0 ]; then
            if [ $FETCHES -gt ${MAX_FETCHES} ]; then
                echo "Failed to fetch CosmosDB Emulator certificate after ${MAX_FETCHES} attempts."
                exit 1
            fi
            echo "Failed to fetch CosmosDB Emulator certificate. Retrying in 10 seconds..."
            FETCHES=$((FETCHES + 1))
            sleep 10
        else
            FETCH="DONE"
        fi

        if [ $FETCH == "DONE" ]; then
            echo "Successfully fetched CosmosDB Emulator certificate after ${FETCHES} attempts."

            cp ~/emulatorcert.crt /usr/local/share/ca-certificates/
            update-ca-certificates
            echo " = CosmosDB Emulator certificate installed ="
        fi
    done
fi

# Start the function server
/azure-functions-host/Microsoft.Azure.WebJobs.Script.WebHost

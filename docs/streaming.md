# Streaming Workflows

`pctasks` supports streaming item creation and ingestion into the pgstac
database. At a high level, Storage Events are persisted to a Cosmos DB
container. A Change Feed monitors that container for new events, and dispatches
them to dataset-specific work queues. By registering a streaming workflow with
`pctasks`, `pctasks` will monitor the storage account and process the messages
from each per-dataset queue.

## Writing a streaming workflow

A streaming workflow is similar to other pctasks workflows, but requires a few
additional properties on the streaming tasks within the workflow:

1. The task must define the streaming-related properties using `args`:

   - `queue_url`
   - `visibility_timeout`
   - `min_replica_count`
   - `max_replica_count`
   - `polling_interval`
   - `trigger_queue_length`

2. The workflow should set the top-level `is_streaming` property to `true`.

In addition to these schema-level requirements, there are some expectations in
how the workflow behaves at runtime. In general, streaming tasks should expect
to run indefinitely. They should continuously process messages from a queue, 
and leave starting, stopping, and scaling to the pctasks framework.

## Registering a streaming workflow

A streaming workflow is registered with `pctasks` like any other workflow,
using the `pctasks` CLI:


```
$ pctasks workflow create path/to/workflow.yaml
```

This will store the workflow in `pctask`'s database, but won't actually start
processing items from the stream.

## Running a streaming workflow

To actually start processing with a streaming workkflow, you need to "submit"
the workflow.

```
$ pctasks workflow submit '<workflow_id>'
```

This will cause the actual compute resources to be created.

## Additional Azure Resources

Streaming workflows require a few additional Azure resources to be created:

1. A Cosmos DB database. This is managed outside of `pctasks`. The source events
   are configured to write to Cosmos DB outside of `pctasks`.
2. An AKS node pool dedicated to running streaming tasks (not technically necessary). This is managed by `pctasks` in `aks.tf`.
3. A Kubernetes namespace for streaming tasks (not technically necessary). This is managed by `pctasks`.
4. A Kubernetes secret for accessing the storage queues.
5. A Helm deployment of KEDA.
6. A KEDA `TriggerAuthentication` object in the same namespace as the streaming tasks.

## Permissions

The tasks running the streaming jobs need some additional permissions. Assuming
you've set `CLIENT_ID`, to the ID of the service principal running tasks and
`SUBSCRIPTION_ID`, `RESOURCE_GROUP`, and `STORAGE_ACCOUNT` to the correct values
for the Storage Account where the messages are being sent.

**pctasks operational storage containers**

`pctasks` uses a set of storage containers to manage task input and output,
logging, and code distribution. For batch tasks, the pctasks service takes care
of generating short-lived SAS tokens. Because streaming tasks are long-lived, we
instead rely on the managed identity having the proper access to each of these
containers (read for `code`, contributor for `taskio` and `status`).

```
❯ az role assignment create \
        --assignee "$CLIENT_ID" \
        --role "Storage Blob Data Contributor" \
        --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Storage/storageAccounts/$STORAGE_ACCOUNT/blobServices/default/containers/taskio"

❯ az role assignment create \
        --assignee "$CLIENT_ID" \
        --role "Storage Blob Data Contributor" \
        --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Storage/storageAccounts/$STORAGE_ACCOUNT/blobServices/default/containers/tasklogs"

❯ az role assignment create \
        --assignee "$CLIENT_ID" \
        --role "Storage Blob Data Reader" \
        --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Storage/storageAccounts/$STORAGE_ACCOUNT/blobServices/default/containers/code"
```

**storage queue**

The streaming workflow tasks will receive messages from a queue, create STAC
items from the message. the `Storage Queue Data Contributor` role is required to
receive and delete the messages when they're successfully processed.

```
❯ az role assignment create \
        --assignee "$CLIENT_ID" \
        --role "Storage Queue Data Contributor" \
        --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Storage/storageAccounts/$STORAGE_ACCOUNT"
```

**Cosmos DB**

The streaming workflow tasks will write their outputs to a Cosmos DB container.
Note that Cosmos DB requires the Object ID of the Enterprise Application associated with your Service Principal.

|          Name          |                                    Description                                     |
| ---------------------- | ---------------------------------------------------------------------------------- |
| COSMOS_DB_ACCOUNT_NAME | The name of your Cosmos DB account                                                 |
| RESOURCE_GROUP         | The name of your resource group                                                    |
| DATABASE_NAME          | The name of the database in your Cosmos DB account                                 |
| CONTAINER_NAME         | The name of the container in your Cosmos DB database                               |
| OBJECT_ID              | The object ID of the enterprise application associated with your service principal |


```
az cosmosdb sql role assignment create \
    --account-name "$COSMOS_DB_ACCOUNT_NAME"
    --resource-group "$RESOURCE_GROUP" \
    --scope "/dbs/$DATABASE_NAME/colls/$CONTAINER_NAME/" \
    --role-definition-id "00000000-0000-0000-0000-000000000002" \
    --principal-id "$OBJECT_ID"
```
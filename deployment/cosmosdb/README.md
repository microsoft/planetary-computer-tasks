# Cosmos DB

Contained in this directory are the scripts used in the Cosmos DB for PCTasks.

## Scripts

The scripts subdirectory contains the stored procedures, triggers, and UDFs for CosmosDB. It is organized
with directory structures by script type and container. The name of the script also contains relevant
information, described below.

### Stored Procedures

Stored procedures are contained in the `scripts/stored_procs` subdirectory. These should be named with the operation and model
they act on, e.g. `PutJobPartitionRun`. The file name without the extension is the ID of the script.

### Triggers

Triggers are stored in the `scripts/triggers` subdirectory. The file name defines 3 fields:
- Whether the trigger is a Pre or Post trigger
- The trigger operation that the trigger applies to
- The remainder of the ID of the trigger

These three pieces of information are separated by a `-` symbol. For instance:

`scripts/triggers/workflow-runs/post-all-workflowruns.js` would be a post-trigger that applies to all trigger operations on the container `workflow-runs` and the trigger ID is `post-all-workflowruns`.

### UDFs

We currently do not have any UDFs defined.
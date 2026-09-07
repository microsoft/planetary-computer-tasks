# Execution Overview

What happens when you submit a `pctasks` workflow? This section gives an overview.

Let's consider an example

```
$ pctasks dataset process-items -d datasets/naip/dataset.yaml chunkset-id
```

That command doesn't actually submit a workflow. The `dataset` group of the CLI is responsible for generating full workflows from a `dataset.yaml`. If we append `--upsert --submit` to the command, the workflow will actually run

```
$ pctasks dataset process-items -d datasets/naip/dataset.yaml chunkset-id
```

This has submitted a workflow run to the **pctasks server** your local environment is configured to talk to.
Check this with `pctasks profile list`

```
$ pctasks profile list

 ___   ___  _____            _
| _ \ / __||_   _| __ _  ___| |__ ___
|  _/| (__   | |  / _` |(_-/| / /(_-/
|_|   \___|  |_|  \__/_|/__/|_\_\/__/

                                    Profiles                                     
┏━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Profile        ┃                                                     Endpoint ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ dev            │                                 http://localhost:8500/tasks/ │
├────────────────┼──────────────────────────────────────────────────────────────┤
│ prod           │         https://planetarycomputer.microsoft.com/api/tasks/v1 │
├────────────────┼──────────────────────────────────────────────────────────────┤
│ test (current) │             https://pctaskstest-staging.azure-api.net/tasks/ │
└────────────────┴──────────────────────────────────────────────────────────────┘
```

What happens next depends on how that server is configured to execute tasks.
We'll go through each.

## Remote Execution with Azure Batch

Your local `pctasks` client is talking to a `pctasks-server` that's somehow
configured to execute workflows. Typically, it's configured to execute tasks as
Jobs in Azure Batch or AKS. Monitoring those jobs is somewhat computationally
expensive, so to avoid overloading the `pctasks-server`, it offloads that to an
Argo Workflow.

So the workflow is

1. Client submits a workflow
2. Server creates an Argo Workflow to monitor that workflow run
3. Argo Workflow creates the Batch Job, Tasks
4. Tasks run in Azure Batch

To debug each of these stages you would check:

1. Did my workflow run get submitted? Check `pctasks runs status <run-id>`
2. Did the Argo Workflow get created? Check the Argo UI look for the argo
   workflow pods and pod logs in the Kubernetes cluster. The argo pods are
   typically in the `pc` namespace for remote deployments, and the `argo`
   namespace for local kind cluster deployments.
3. Did the Batch Job get created? Check in [Batch
   Explorer](https://azure.github.io/BatchExplorer/).

## Local Execution

As part of [](#setup), `./scripts/server` brought up a pctasks server configured
to run workflows locally in docker containers.
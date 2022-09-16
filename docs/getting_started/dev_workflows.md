# Running a workflow in the dev environment

This page will show you how to submit a simple job to the development environment.
We'll use an existing dataset to ingest the STAC Collection and a single Item into the
development database, and then view that Collection and Item via stac-browser.

## Setup

### Setting up the development environment

Follow the instructions for {doc}`/development/setup`

### Creating the settings file

In the environment that PCTasks was installed into (via `scripts/install`), run:

```
> pctasks profile create dev-local
```

This will create a profile named `dev-local`. This can be used to submit jobs to the services run `scripts/server` (not the Kind cluster). Use the following values:

```shell
Enter API endpoint: http://localhost:8510/tasks
Enter API key: hunter2
Confirmation required? [y/n] (y): n
Default arguments:
  Add new default? [y/n] (n): y
    Enter key: registry
    Enter value: localhost:5001
  Add new default? [y/n] (n): n
```

We can also create a profile for submitting to the local Kind cluster. Use:

```
> pctasks profile create dev-cluster
```

with these values:

```shell
Enter API endpoint: http://localhost:8500/tasks
Enter API key: kind-api-key
Confirmation required? [y/n] (y): n
Default arguments:
  Add new default? [y/n] (n): y
    Enter key: registry
    Enter value: localhost:5001
  Add new default? [y/n] (n): n
```

## Running a workflow

We can now set pctasks to use either the dev-local or dev-cluster profile. For the rest of this example we'll use the dev-cluster profile:

```shell
> pctasks profile set dev-cluster
```

You can test running a pctasks workflow by using the `examples/list-logs.yaml` workflow:

```shell
> pctasks submit workflow examples/list-logs.yaml
```

You should see output similar to:

```shell
 ___   ___  _____            _
| _ \ / __||_   _| __ _  ___| |__ ___
|  _/| (__   | |  / _` |(_-/| / /(_-/
|_|   \___|  |_|  \__/_|/__/|_\_\/__/

Submitted workflow with run ID:
1df8cea3166c4f7383b1a5198cb5d7be
```

### Troubleshooting

If you experience issues with the above step, take a look at some of these common issues:

- If using `dev-cluster`, make sure you've set up the cluster with `scripts/cluster setup`.
- If using `dev-local`, make sure you have `scripts/server` running in a separate terminal, or have run `scripts/server --detached`, to ensure services are up.
- If using `dev-cluster` and the cluster has not been recreated for a while (e.g. after machine restarts), the services may not operate properly. Use `scripts/cluster recreate` to recreate the cluster.

## Checking status

### Using pctasks records

Using the run ID from the previous step, you can watch the execution status of the workflow using:

```shell
> pctasks records show workflow --watch ${RUN_ID}
```

This may return instantly, since the workflow should run quickly. However you can use this command with the `--watch` option to poll the API for status and update the console until the job completes.

Once it completes, you should see something like:

```shell
 ___   ___  _____            _
| _ \ / __||_   _| __ _  ___| |__ ___
|  _/| (__   | |  / _` |(_-/| / /(_-/
|_|   \___|  |_|  \__/_|/__/|_\_\/__/

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┓
┃                                     ┃ status         ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━┩
│ Workflow: List log files in Azurite │ ✅ Completed   │
│  - Job: list-logs-job               │  ✅ Completed  │
│     - Task:list-logs-task           │   ✅ Completed │
└─────────────────────────────────────┴────────────────┘
```

### Argo logs

If using `dev-cluster`, you should be able to see the workflow executing in the Argo UI. Go to <http://localhost:8500/argo> and look for your workflow. Argo Workflows with the prefix "wkflw" contains logs for the runner that executes the workflow. The dev cluster also uses Argo to execute tasks; look for Argo Workflows with the prefix "task" to see the logs for those tasks.

## Fetch the task logs

You can fetch detailed with the workflow using:

```shell
> pctasks records fetch workflow ${RUN_ID}
```

You can also list jobs and tasks, e.g.

```shell
> pctasks records list tasks ${RUN_ID} list-logs-job
```

To get the log file for the task, use:

```shell
> pctasks records fetch logs ${RUN_ID} list-logs-job list-logs-task
```
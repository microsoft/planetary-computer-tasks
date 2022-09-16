# Templating

PCTasks uses templating in workflow and dataset YAML to enable dynamic values to be used. This guide describes how templates are
used and what templating functions are available.

## Overview

Templating is used to determine workflow values dynamically. Template expressions are wrapped with `${{` and `}}`, for example

```yaml
src: ${{ local.path(./chesapeake_lulc.py) }}
```

The template values or functions are all grouped with the first term; in the example above, the `path` function is in the
template group `local`. The available groups are described below.

Template substitution can be both processed on the client side, before workflow submission, and on the server side. For example, the `local` functions are evaluated before workflow submission, whereas the `secrets` template expressions are evaluated on the server side to securely inject secrets from Azure KeyVault into task runners.

## Template groups

### args

The `args` group allows access to [](arguments). The argument names are accessed through dot notation, e.g. `args.registry` references the value of the
`registry` argument.

### secrets

The secrets template group is the mechanism for injecting secrets, such as credentials, into task environments. The secrets group template can only be used with the `environment` or `tokens` section of workflows and tasks.

Secrets are the way to get sensitive information into the execution of your tasks. Secrets are injected into tasks through
a template that is evaluated on by the PCTasks workflow executor before submitting the task for execution. For deployed
PCTasks systems, the secrets are fetched from a key vault that is manually maintained by an administrator.

For example, using `${{ secrets.task-tenant-id }}` will fetch the KeyVault Secret value for a secret named `task-tenant-id`.

Eventually we plan to support user-driven secret management, similar to GitHub Encrypted Secrets. However, for now if
you need to know what secrets are available to you or need a new secret to be put in place, contact your administrator.

### jobs

The `jobs` template group enables access to the outputs of tasks for a job that is run prior to the job where the template is used. For example, you can reference the output of task `task3` of a job with an id `job1` through `${{ job.job1.tasks.task3.output }}`. This template group is evaluated
while the job is being executed, so as long as the output of the referenced job was collected by the PCTask workflow executor the correct value will
be templated in. If there is an issue with templating this group, the workflow will fail with a templating error before the job starts executing, but after previous jobs have executed.

Example:
```yaml
jobs:
  job1:
    tasks:
      - id: task1a
        ...
  job2:
    tasks:
      - id: task2a
        args:
          x: ${{ jobs.job1.tasks.task1a.output }}
```

Note that you can reference into objects or lists from the output, which is the object representation of the output model for a task (type 'U' of `Task[T, U]`, which is a pydantic model).

Example:
```yaml
jobs:
  job1:
    tasks:
      - id: task1a
        ...
  job2:
    tasks:
      - id: task2a
        args:
          x: ${{ jobs.job1.tasks.task1a.output.infos[0].x }}
```

### tasks

Similar to the `jobs` group, the `tasks` group can be used to get the output of tasks that have run previously in the same job.

Example:
```yaml
jobs:
  job1:
    tasks:
      - id: task1a
        ...
      - id: task2a
        args:
          x: ${{ tasks.task1a.output }}
```

(item_template_group)=
### item

The `item` template group is used when a job defines a [](foreach) configuration. You can reference into the item if item is an object value,
index into item if it is a list.

### local

The `local` group provides functions for working with the local file system. In all cases, relative file paths
are relative to the workflow file path if that is available, or the current working directory if the workflow
was not constructed from a file.

#### local.file

The `local.file` function will read in the contents of a local JSON file and template in the contents as an object.

Example:
```yaml
task:
  - id: ingest-collection
    args:
      collection: ${{ local.file(./collection.json) }}
```

#### local.path

Template in the absolute path of a file. Useful to ensure file paths are read the same no matter the current working directory of the
PCTasks client.

Example:
```yaml
code:
  src: ${{ local.path(./chesapeake_lulc.py) }}
  requirements: ${{ local.path(./requirements.txt) }}
```

(pc_template_group)=

### pc

The `pc` template group is used to interact with the Planetary Computer API.

#### pc.get_token

The `get_token` function allows you to call the Planetary Computer [Data Auth API](https://planetarycomputer.microsoft.com/docs/concepts/sas/) to
generate a SAS token. It takes two arguments - the first being the storage account, the second being the container.

Example:
```yaml
tokens:
  sentinel2l2a01:
    containers:
      sentinel2-l2: ${{ pc.get_token(sentinel2l2a01, sentinel2-l2) }}
```

_Note:_ The SAS tokens generated by this API will last 1 hour. We plan to expand this template function with the ability to request
a longer duration token using a Planetary Computer account API key.
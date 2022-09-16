# Workflows

Workflows are the core unit of work executed by PCTasks. Workflows can execute one or many tasks. A workflow is configured through YAML
or by constructing Pydantic models in Python code. Workflows are submitted to the PCTasks API. Upon submission, a workflow can
be assigned values for arguments or a a trigger event, either of which can be used to provide values for templates inside the
workflow configuration. When a workflow is run, it is assigned a "Run ID", which is the unique identifier that can be used to
interact with that specific instantiation of a workflow run.

Note that the layout and language of PCTasks workflows is heavily based on [GitHub Actions](https://docs.github.com/en/actions/using-workflows/about-workflows), and many GitHub Actions concepts are reflected in PCTasks.

## Workflow configuration

A workflow configuration defines everything that PCTasks needs to know in order to execute a workflow, with the exception of argument values or trigger events, which are defined at the time of submitting the workflow. See the [examples](https://github.com/microsoft/planetary-computer-tasks/tree/main/examples) in the PCTasks GitHub repository for
examples of workflow configurations.

The following configuration can be defined at the workflow level:

### dataset

REQUIRED. Defines the dataset this workflow pertains to. The dataset identifier is in the format `{owner}/{dataset}`.

Example:
```yaml
dataset: microsoft/goes-r
```

_Note:_ The `owner` component of the ID is a placeholder, and all current datasets should have owner `microsoft`.

(arguments)=
### args

Arguments define the required values that should be supplied when a workflow is submitted. The arguments defined in the configuration
is a list of variable names that can then be used in templates throughout the workflow configuration.

Example:
```yaml
args:
- registry
- platform
```

For the above, whenever this workflow is submitted, the API caller will need to supply values for the `registry` and `platform` arguments.


### tokens

The `tokens` section allows the workflow to define Azure Storage Shared Access Signature (SAS) tokens for storage accounts and containers.
These tokens can be supplied directly (not recommended), through a template function like `pc.get_token(...)` (see [](pc_template_group) docs),
or through a secret (see [](../user_guide/secrets)).

Example:
```yaml
tokens:
  sentinel2l2a01:
    containers:
      sentinel2-l2: ${{ pc.get_token(sentinel2l2a01, sentinel2-l2) }}
```

## Jobs configuration

Jobs are simply groups of tasks that get executed in sequence.

_Note:_ Currently PCTasks will execute Jobs in sequence as they are defined. In the future we plan to provide the option to execute
Jobs that do not have dependencies on each other in parallel.

### Using `foreach` in Jobs

The `foreach` configuration is the key to distributed processing of data using PCTasks. It's also a key differentiator to GitHub Actions, which does not have a similar concept. The `foreach` in PCTasks is a similar concept to other workflow execution frameworks, like `withItems` in [Argo Workflows](https://argoproj.github.io/argo-workflows/walk-through/loops/).

A `foreach` section defines the `items` that will be used to generate "sub-jobs". The value or properties of each element of `items` can be accessed through the [](item_template_group) template group. Each of the sub-jobs will be executed in parallel, with each task contained in the sub-jobs executed sequentially.

Example:
```yaml
jobs:
  job1:
    foreach:
        items:
        - one
        - two
        - three
```

More useful then specifying a list of items, you can use the output of a previous job's task to
distribute processing over the results.

Example:
```yaml
jobs:
  job1:
    # Job with task "task1" that outputs a list of URIs
  job2:
    foreach:
      items: ${{ jobs.job1.tasks.task1.output.uris }}
    # Now use ${{ item }} as the URI to task input
```

When viewing records of a run, you'll notice that the job names have an index. For instance, in the above
example, there would be no `job2`, but instead a set of jobs named `job2[0]`, `job2[1]`, etc. Each of the
sub-jobs execute as if they were a distinct PCTasks job after being templated with the `foreach`.


## Task configuration

Tasks are the core unit of work for PCTasks. Workflows and Jobs are really containers that organize Tasks, which is
what defines the actual code to be executed in the system.

Tasks are defined in a list under a job, for example:

```yaml
jobs:
  job1:
    tasks:
      - id: task1
        task: pctasks.task.common.list_prefixes:task
        args:
          src_uri: blob://mysa/mycontainer
        image: pccomponents.azurecr.io/pctasks-task-base:latest
```

### task

The `task` property of a task configuration is what determines the code that will be executed when running the task.
It is a "task path" that points to a instance of a subclass of [](../reference/generated/pctasks.task.task.Task), or do a callable (e.g. a function)
that returns a Task instance.

The task path is stated using [Entry Points syntax](https://setuptools.pypa.io/en/latest/userguide/entry_point.html#entry-points-syntax).

### image and image_key

You must supply one of either `image` or `image_key` - normally `image`. This defines the image that will be used to run
the task. It must at least have `pctasks` installed. And, if no `code` section is defined (as described below), it should have
the module referenced in the `task` definition on the PYTHONPATH.

Example:
```yaml
image: pccomponents.azurecr.io/pctasks-task-base:latest
```

An `image_key` must be registered with the PCTask deployment by an admin - it is used to reference a specific image with optional environment and tags
defined based on a single key.

Example
```yaml
image_key: ingest
```

### code

An optional `code` configuration allows users to upload a python file or a python module to put on the PYTHONPATH before attempting to load
the Task at the task path. You can also supply a requirements.txt file with dependencies that should be pip-installed before
running a task. See [](./runtime) for more details.

### args

`args` is an object that defines the `Task[T, U]` input model (type T, which must subclass a Pydantic model). The args will be validated
against the input model at task runtime.

### environment

You can define key/value pairs to load into the environment before running the task. This is useful for setting things like Azure SDK
credentials using [](../user_guide/secrets), or anything else that is required to run the task.

### tags

Tags is an arbitrary object that lists tags as keys and values. This can be used to transfer information to PCTasks system components.
For instance, tagging a task with the key `batch_pool_id` will ensure that the Azure Batch tasks are submitted to a specific node pool.
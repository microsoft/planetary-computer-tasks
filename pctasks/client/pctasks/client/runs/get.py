import click


@click.group("get")
def get_cmd() -> None:
    """Get a record, logs or events."""
    pass


@get_cmd.command("workflow")
@click.argument("run_id")
@click.option("-s", "--status", is_flag=True, help="Only report status.")
@click.pass_context
def get_workflow_run_cmd(ctx: click.Context, run_id: str, status: bool) -> int:
    """Fetch a workflow run record.

    Outputs the YAML of the record to stdout.
    """
    from . import _get

    return _get.get_workflow_run(ctx, run_id, status)


@get_cmd.command("partition")
@click.argument("run_id")
@click.argument("job_id")
@click.option("-p", "--partition", "partition_id", default="0", help="Partition ID.")
@click.pass_context
def get_job_partition_cmd(
    ctx: click.Context, run_id: str, job_id: str, partition_id: str
) -> int:
    """Fetch a job partition record. Defaults to partition 0 if not specified.

    Outputs the YAML of the record to stdout.
    """
    from . import _get

    return _get.get_job_partition(ctx, run_id, job_id, partition_id)


@get_cmd.command("run-log")
@click.argument("run_id")
@click.pass_context
def get_workflow_log_cmd(ctx: click.Context, run_id: str) -> int:
    """Fetch a run log.

    Outputs the text of the workflow run log to stdout.
    """
    from . import _get

    return _get.get_workflow_log(ctx, run_id=run_id)


@get_cmd.command("task-log")
@click.argument("run_id")
@click.argument("job_id")
@click.argument("task_id")
@click.option("-p", "--partition", "partition_id", default="0", help="Partition ID.")
@click.pass_context
def get_task_log_cmd(
    ctx: click.Context, job_id: str, task_id: str, run_id: str, partition_id: str
) -> int:
    """Fetch a task log.

    Outputs the text of the task run log to stdout.
    """
    from . import _get

    return _get.get_task_log(
        ctx, run_id=run_id, job_id=job_id, partition_id=partition_id, task_id=task_id
    )

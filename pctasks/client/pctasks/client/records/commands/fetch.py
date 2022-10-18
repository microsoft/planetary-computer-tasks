import click


@click.command("workflow")
@click.argument("workflow_id")
@click.pass_context
def fetch_workflow_cmd(ctx: click.Context, workflow_id: str) -> int:
    """Fetch a workflow run record.

    Outputs the YAML of the record to stdout.
    """
    from . import _fetch

    return _fetch.fetch_workflow_cmd(ctx, workflow_id)


@click.command("workflow-run")
@click.argument("run_id")
@click.option("-s", "--status", is_flag=True, help="Only report status.")
@click.pass_context
def fetch_workflow_run_cmd(ctx: click.Context, run_id: str, status: bool) -> int:
    """Fetch a workflow run record.

    Outputs the YAML of the record to stdout.
    """
    from . import _fetch

    return _fetch.fetch_workflow_run_cmd(ctx, run_id, status)


@click.command("job-partition")
@click.argument("run_id")
@click.argument("job_id")
@click.option("-p", "--partition", "partition_id", default="0", help="Partition ID.")
@click.pass_context
def fetch_job_partition_cmd(
    ctx: click.Context, run_id: str, job_id: str, partition_id: str
) -> int:
    """Fetch a job partition record. Defaults to partition 0 if not specified.

    Outputs the YAML of the record to stdout.
    """
    from . import _fetch

    return _fetch.fetch_job_part_cmd(ctx, run_id, job_id, partition_id)


@click.command("task-log")
@click.argument("run_id")
@click.argument("job_id")
@click.argument("task_id")
@click.option("-p", "--partition", "partition_id", default="0", help="Partition ID.")
@click.pass_context
def fetch_task_log_cmd(
    ctx: click.Context, job_id: str, task_id: str, run_id: str, partition_id: str
) -> int:
    """Fetch a task record.

    Outputs the YAML of the record to stdout.
    """
    from . import _fetch

    return _fetch.fetch_task_log_cmd(
        ctx, run_id=run_id, job_id=job_id, partition_id=partition_id, task_id=task_id
    )


@click.group("fetch")
def fetch_cmd() -> None:
    """Fetch a record, logs or events."""
    pass


fetch_cmd.add_command(fetch_workflow_cmd)
fetch_cmd.add_command(fetch_workflow_run_cmd)
fetch_cmd.add_command(fetch_job_partition_cmd)
fetch_cmd.add_command(fetch_task_log_cmd)

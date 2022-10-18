import click


@click.command("workflows")
@click.pass_context
def list_workflows_cmd(ctx: click.Context) -> int:
    """List workflow runs for a workflow."""
    from . import _list

    return _list.list_workflows_cmd(ctx)


@click.command("workflow-runs")
@click.argument("workflow_id")
@click.pass_context
def list_workflow_runs_cmd(ctx: click.Context, workflow_id: str) -> int:
    """List workflow runs for a workflow."""
    from . import _list

    return _list.list_workflow_runs_cmd(ctx, workflow_id)


@click.command("job-partitions")
@click.argument("run_id")
@click.argument("job_id")
@click.pass_context
def list_job_partition_cmd(ctx: click.Context, run_id: str, job_id: str) -> int:
    """list a job partition record. Defaults to partition 0 if not specified.

    Outputs the YAML of the record to stdout.
    """
    from . import _list

    return _list.list_job_part_cmd(ctx, run_id, job_id)


# @click.command("logs")
# @click.argument("run_id")
# @click.argument("job_id")
# @click.argument("task_id")
# @click.option("-p", "--partition", "partition_id", default="0", help="Partition ID.")
# @click.pass_context
# def list_logs_cmd(
#     ctx: click.Context, job_id: str, task_id: str, run_id: str, partition_id: str
# ) -> int:
#     """list a task record.

#     Outputs the YAML of the record to stdout.
#     """
#     from . import _list

#     return _list.list_task_log_cmd(ctx, job_id, task_id, run_id, partition_id)


@click.group("list")
def list_cmd() -> None:
    """List records."""
    pass


list_cmd.add_command(list_workflows_cmd)
list_cmd.add_command(list_workflow_runs_cmd)
list_cmd.add_command(list_job_partition_cmd)
# list_cmd.add_command(list_logs_cmd)

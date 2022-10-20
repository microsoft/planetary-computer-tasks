from typing import Optional

import click


@click.group("list")
def list_cmd() -> None:
    """List records."""
    pass


@list_cmd.command("workflows")
@click.argument("workflow_id")
@click.option("-s", "--sort-by", help="Property to sort by")
@click.option("-d", "--desc", help="Sort descending", is_flag=True)
@click.pass_context
def list_workflow_runs_cmd(
    ctx: click.Context, workflow_id: str, sort_by: Optional[str], desc: bool
) -> None:
    """List workflow runs for a workflow."""
    from . import _list

    ctx.exit(_list.list_workflow_runs_cmd(ctx, workflow_id, sort_by=sort_by, desc=desc))


@list_cmd.command("partitions")
@click.argument("run_id")
@click.argument("job_id")
@click.pass_context
def list_job_partition_cmd(ctx: click.Context, run_id: str, job_id: str) -> None:
    """list a job partition record. Defaults to partition 0 if not specified.

    Outputs the YAML of the record to stdout.
    """
    from . import _list

    ctx.exit(_list.list_job_part_cmd(ctx, run_id, job_id))

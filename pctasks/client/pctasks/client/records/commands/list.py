from typing import Optional

import click

from pctasks.client.records.commands.options import opt_all, opt_page, opt_status


@click.command("workflows")
@click.argument("dataset")
@opt_page
@opt_all
@opt_status
@click.option(
    "--ids",
    is_flag=True,
    help="Print list of workflow run IDs out to stdout.",
)
@click.pass_context
def list_workflows_cmd(
    ctx: click.Context,
    dataset: str,
    page: bool,
    all: bool,
    status: Optional[str],
    ids: bool,
) -> None:
    from . import _list

    return _list.list_workflows_cmd(ctx, dataset, page, all, status, ids)


@click.command("jobs")
@click.argument("run_id")
@opt_page
@opt_all
@opt_status
@click.option(
    "--ids",
    is_flag=True,
    help="Print list of job IDs out to stdout.",
)
@click.pass_context
def list_jobs_cmd(
    ctx: click.Context,
    run_id: str,
    page: bool,
    all: bool,
    status: Optional[str],
    ids: bool,
) -> None:
    from . import _list

    return _list.list_jobs_cmd(ctx, run_id, page, all, status, ids)


@click.command("tasks")
@click.argument("run_id")
@click.argument("job_id")
@opt_page
@opt_all
@opt_status
@click.option(
    "--ids",
    is_flag=True,
    help="Print list of task IDs out to stdout.",
)
@click.pass_context
def list_tasks_cmd(
    ctx: click.Context,
    run_id: str,
    job_id: str,
    page: bool,
    all: bool,
    status: Optional[str],
    ids: bool,
) -> None:
    from . import _list

    return _list.list_tasks_cmd(ctx, run_id, job_id, page, all, status, ids)


@click.group("list")
def list_cmd() -> None:
    """List records."""
    pass


list_cmd.add_command(list_workflows_cmd)
list_cmd.add_command(list_jobs_cmd)
list_cmd.add_command(list_tasks_cmd)

from typing import Optional

import click
from rich.console import Console

from pctasks.cli.cli import cli_output
from pctasks.client.client import PCTasksClient
from pctasks.client.records.commands.options import opt_all, opt_page, opt_status
from pctasks.client.records.render import render_jobs, render_tasks, render_workflows
from pctasks.client.settings import ClientSettings


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

    ds: Optional[str] = None if dataset == "all" else dataset

    settings = ClientSettings.from_context(ctx.obj)
    client = PCTasksClient(settings)
    console = Console(stderr=True)
    with console.status("Fetching records...") as fetch_status:
        fetch_status.update(
            status="[bold green]Fetching records...",
            spinner="aesthetic",
            spinner_style="green",
        )
        workflows = client.get_workflows(dataset_id=ds)

        if status:
            workflows = [w for w in workflows if w.status == status]

    if ids:
        cli_output("\n".join([w.run_id for w in workflows]))
    else:
        render_workflows(
            console=console, workflows=workflows, show_all=all, page_results=page
        )


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

    settings = ClientSettings.from_context(ctx.obj)
    client = PCTasksClient(settings)
    console = Console(stderr=True)
    with console.status("Fetching records...") as fetch_status:
        fetch_status.update(
            status="[bold green]Fetching records...",
            spinner="aesthetic",
            spinner_style="green",
        )
        jobs = client.get_jobs(run_id=run_id)

        if status:
            jobs = [j for j in jobs if j.status == status]

    if ids:
        cli_output("\n".join([j.job_id for j in jobs]))
    else:
        render_jobs(console=console, jobs=jobs, show_all=all, page_results=page)


@click.command("tasks")
@click.argument("job_id")
@click.argument("run_id")
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
    job_id: str,
    run_id: str,
    page: bool,
    all: bool,
    status: Optional[str],
    ids: bool,
) -> None:

    settings = ClientSettings.from_context(ctx.obj)
    client = PCTasksClient(settings)
    console = Console(stderr=True)
    with console.status("Fetching records...") as fetch_status:
        fetch_status.update(
            status="[bold green]Fetching records...",
            spinner="aesthetic",
            spinner_style="green",
        )
        tasks = client.get_tasks(job_id=job_id, run_id=run_id)

        if status:
            tasks = [t for t in tasks if t.status == status]

    if ids:
        cli_output("\n".join([t.task_id for t in tasks]))
    else:
        render_tasks(console=console, tasks=tasks, show_all=all, page_results=page)


@click.group("list")
def list_cmd() -> None:
    """List records."""
    pass


list_cmd.add_command(list_workflows_cmd)
list_cmd.add_command(list_jobs_cmd)
list_cmd.add_command(list_tasks_cmd)

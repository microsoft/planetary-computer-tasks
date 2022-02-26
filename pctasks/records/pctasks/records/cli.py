from datetime import datetime, timedelta
from typing import Any, Callable, Optional

import click
import pandas as pd
from rich.console import Console
from rich.syntax import Syntax

from pctasks.core.models.dataset import DatasetIdentifier
from pctasks.core.models.record import WorkflowRunRecord
from pctasks.core.storage import read_text
from pctasks.core.utils import map_opt
from pctasks.records.console.dataframe import DataFrameRender
from pctasks.records.query import query_logs
from pctasks.records.render import render_jobs, render_tasks, render_workflows
from pctasks.records.settings import RecordsSettings


def opt_page(fn: Callable[..., Any]) -> Callable[..., Any]:
    _opt = click.option("-p", "--page", is_flag=True, help="Page output.")
    _opt(fn)
    return fn


def opt_all(fn: Callable[..., Any]) -> Callable[..., Any]:
    _opt = click.option(
        "-a", "--all", is_flag=True, help="Print all output, even if large."
    )
    _opt(fn)
    return fn


def opt_status(fn: Callable[..., Any]) -> Callable[..., Any]:
    _opt = click.option("-s", "--status", help="Filter by status.")
    _opt(fn)
    return fn


@click.command("workflows")
@click.argument("dataset")
@opt_page
@opt_all
@opt_status
@click.pass_context
def show_workflows_cmd(
    ctx: click.Context, dataset: str, page: bool, all: bool, status: Optional[str]
) -> None:

    ds: Optional[DatasetIdentifier] = (
        DatasetIdentifier.from_string(dataset) if not dataset == "all" else None
    )
    settings = RecordsSettings.from_context(ctx.obj)
    console = Console()
    with console.status("Fetching records...") as fetch_status:
        fetch_status.update(
            status="[bold green]Fetching records...",
            spinner="aesthetic",
            spinner_style="green",
        )
        with settings.tables.get_workflow_run_record_table() as table:
            if ds:
                workflows = table.get_workflow_runs(ds)
            else:
                workflows = table.get_records()

        if status:
            workflows = [w for w in workflows if w.status == status]

    render_workflows(
        console=console, workflows=workflows, show_all=all, page_results=page
    )


@click.command("workflow")
@click.argument("run_id")
@click.option("-d", "--dataset", help="Filter by dataset.")
@opt_page
@click.pass_context
def show_workflow_cmd(
    ctx: click.Context,
    run_id: str,
    dataset: Optional[str],
    page: bool,
) -> None:

    ds: Optional[DatasetIdentifier] = map_opt(
        lambda x: DatasetIdentifier.from_string(x), dataset
    )
    settings = RecordsSettings.from_context(ctx.obj)
    console = Console()
    with console.status("Fetching records...") as fetch_status:
        fetch_status.update(
            status="[bold green]Fetching records...",
            spinner="aesthetic",
            spinner_style="green",
        )
        if ds:
            with settings.tables.get_workflow_run_record_table() as table:
                w = table.get_record(table.get_run_record_id(ds, run_id))
                if not w:
                    console.print(
                        f"No workflow for {ds} found with run_id {run_id}",
                        style="bold red",
                    )
                    return
                workflow: WorkflowRunRecord = w
        else:
            with settings.tables.get_workflow_run_record_table() as table:
                w = table.get_workflow_run(run_id)
                if not w:
                    console.print(
                        f"No workflow found with run_id {run_id}",
                        style="bold red",
                    )
                    return
                workflow = w

    console.print(Syntax(workflow.to_yaml(), "yaml"))


@click.command("jobs")
@click.argument("run_id")
@opt_page
@opt_all
@opt_status
@click.pass_context
def show_jobs_cmd(
    ctx: click.Context, run_id: str, page: bool, all: bool, status: Optional[str]
) -> None:

    settings = RecordsSettings.from_context(ctx.obj)
    console = Console()
    with console.status("Fetching records...") as fetch_status:
        fetch_status.update(
            status="[bold green]Fetching records...",
            spinner="aesthetic",
            spinner_style="green",
        )
        with settings.tables.get_job_run_record_table() as table:
            jobs = table.get_jobs(run_id)

        if status:
            jobs = [j for j in jobs if j.status == status]

    render_jobs(console=console, jobs=jobs, show_all=all, page_results=page)


@click.command("job")
@click.argument("job_id")
@click.argument("run_id")
@click.pass_context
def show_job_cmd(
    ctx: click.Context,
    job_id: str,
    run_id: str,
) -> None:

    settings = RecordsSettings.from_context(ctx.obj)
    console = Console()
    with console.status("Fetching records...") as fetch_status:
        fetch_status.update(
            status="[bold green]Fetching records...",
            spinner="aesthetic",
            spinner_style="green",
        )
        with settings.tables.get_job_run_record_table() as table:
            job = table.get_record(table.get_run_record_id(run_id, job_id))
            if not job:
                console.print(
                    f"No job for {run_id} {job_id} found",
                    style="bold red",
                )
                return

    console.print(Syntax(job.to_yaml(), "yaml"))


@click.command("tasks")
@click.argument("job_id")
@click.argument("run_id")
@opt_page
@opt_all
@opt_status
@click.pass_context
def show_tasks_cmd(
    ctx: click.Context,
    job_id: str,
    run_id: str,
    page: bool,
    all: bool,
    status: Optional[str],
) -> None:

    settings = RecordsSettings.from_context(ctx.obj)
    console = Console()
    with console.status("Fetching records...") as fetch_status:
        fetch_status.update(
            status="[bold green]Fetching records...",
            spinner="aesthetic",
            spinner_style="green",
        )
        with settings.tables.get_task_run_record_table() as table:
            tasks = table.get_tasks(run_id, job_id)

        if status:
            tasks = [t for t in tasks if t.status == status]

    render_tasks(console=console, tasks=tasks, show_all=all, page_results=page)


@click.command("task")
@click.argument("job_id")
@click.argument("task_id")
@click.argument("run_id")
@click.pass_context
def show_task_cmd(
    ctx: click.Context,
    job_id: str,
    task_id: str,
    run_id: str,
) -> None:

    settings = RecordsSettings.from_context(ctx.obj)
    console = Console()
    with console.status("Fetching records...") as fetch_status:
        fetch_status.update(
            status="[bold green]Fetching records...",
            spinner="aesthetic",
            spinner_style="green",
        )
        with settings.tables.get_task_run_record_table() as table:
            task = table.get_record(table.get_run_record_id(run_id, job_id, task_id))
            if not task:
                console.print(
                    f"No task for {run_id} {job_id} found with task_id {task_id}",
                    style="bold red",
                )
                return

    console.print(Syntax(task.to_yaml(), "yaml"))


@click.command("logs")
@click.argument("job_id")
@click.argument("task_id")
@click.argument("run_id")
@click.option("-i", "--index", default=-1, help="Index of log to show")
@opt_page
@click.pass_context
def show_logs_cmd(
    ctx: click.Context,
    job_id: str,
    task_id: str,
    run_id: str,
    index: int,
    page: bool,
) -> None:

    settings = RecordsSettings.from_context(ctx.obj)
    console = Console()
    with console.status("Fetching logs...") as fetch_status:
        fetch_status.update(
            status="[bold green]Fetching logs...",
            spinner="aesthetic",
            spinner_style="green",
        )
        with settings.tables.get_task_run_record_table() as table:
            task = table.get_record(table.get_run_record_id(run_id, job_id, task_id))
            if not task:
                console.print(
                    f"No task for {job_id}/{task_id} {run_id}",
                    style="bold red",
                )
                return

        logs = task.log_uris
        if not logs:
            console.print(
                f"No logs for task {job_id}/{task_id} {run_id}",
                style="bold red",
            )
            return

        if index - 1 > len(logs) or index < -len(logs):
            console.print(
                f"Invalid index. Must be between {-len(logs)} and {len(logs)-1}",
                style="bold red",
            )
        log = logs[index]

        txt = read_text(
            log,
            sas_token=settings.logs_sas_token,
            account_key=settings.logs_account_key,
            account_url=settings.logs_account_url,
        )

    if page:
        with console.pager():
            console.print(txt)
    else:
        print("")
        console.print(txt)


@click.command("events")
@click.argument("run_id")
@opt_page
@opt_all
@click.pass_context
def show_events_cmd(ctx: click.Context, run_id: str, page: bool, all: bool) -> None:
    settings = RecordsSettings.from_context(ctx.obj)
    query = f"""
    AppEvents
    | where Properties['run_id'] == '{run_id}'
    | project TimeGenerated, Message = Name
    | order by TimeGenerated asc
    """
    if not settings.app_insights_workspace_id:
        raise click.UsageError("App Insights workspace id not set")

    console = Console()
    with console.status("Fetching records...") as fetch_status:
        fetch_status.update(
            status="[bold green]Fetching events...",
            spinner="aesthetic",
            spinner_style="green",
        )
        df = pd.DataFrame(
            query_logs(
                query,
                datetime.utcnow() - timedelta(days=10),
                datetime.utcnow(),
                settings.app_insights_workspace_id,
            ),
            columns=["TimeGenerated", "Message"],
        )

    DataFrameRender(console, df, all=all).render(page=page)


@click.group("show")
def show_cmd() -> None:
    """Query and show records from PCTasks."""
    pass


show_cmd.add_command(show_workflows_cmd)
show_cmd.add_command(show_workflow_cmd)
show_cmd.add_command(show_jobs_cmd)
show_cmd.add_command(show_job_cmd)
show_cmd.add_command(show_tasks_cmd)
show_cmd.add_command(show_task_cmd)
show_cmd.add_command(show_logs_cmd)
show_cmd.add_command(show_events_cmd)


@click.group("records")
def records_cmd() -> None:
    """Query and show records from PCTasks."""
    pass


records_cmd.add_command(show_cmd)

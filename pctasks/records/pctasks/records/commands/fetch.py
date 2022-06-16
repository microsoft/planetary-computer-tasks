from datetime import datetime, timedelta
from typing import Callable, Optional, TypeVar

import click
import pandas as pd
from click.exceptions import Exit
from rich.console import Console
from rich.syntax import Syntax

from pctasks.cli.cli import cli_output
from pctasks.core.models.dataset import DatasetIdentifier
from pctasks.core.models.record import (
    JobRunRecord,
    RunRecord,
    TaskRunRecord,
    WorkflowRunRecord,
)
from pctasks.core.storage import read_text
from pctasks.core.utils import map_opt
from pctasks.records.commands.options import opt_all, opt_page
from pctasks.records.console.dataframe import DataFrameRender
from pctasks.records.constants import NOT_FOUND_EXIT_CODE
from pctasks.records.context import RecordsCommandContext
from pctasks.records.query import query_logs
from pctasks.records.settings import RecordsSettings

T = TypeVar("T", bound=RunRecord)


def fetch_record(
    ctx: click.Context, fetch: Callable[[RecordsSettings, Console], Optional[T]]
) -> int:
    records_context: RecordsCommandContext = ctx.obj
    settings = RecordsSettings.from_context(ctx.obj)
    console = Console(stderr=True)
    record: Optional[T] = None
    with console.status("Fetching records...") as fetch_status:
        fetch_status.update(
            status="[bold green]Fetching record...",
            spinner="aesthetic",
            spinner_style="green",
        )
        record = fetch(settings, console)

    if not record:
        raise Exit(NOT_FOUND_EXIT_CODE)

    if records_context.pretty_print:
        console.print(Syntax(record.to_yaml(), "yaml"))
    else:
        cli_output(record.to_yaml())

    return 0


@click.command("workflow")
@click.argument("run_id")
@click.option("-d", "--dataset", help="Filter by dataset.")
@click.pass_context
def fetch_workflow_cmd(
    ctx: click.Context,
    run_id: str,
    dataset: Optional[str],
) -> int:
    """Fetch a workflow record.

    Outputs the YAML of the record to stdout.
    """
    ds: Optional[DatasetIdentifier] = map_opt(
        lambda x: DatasetIdentifier.from_string(x), dataset
    )

    def _fetch(
        settings: RecordsSettings, console: Console
    ) -> Optional[WorkflowRunRecord]:
        if ds:
            with settings.tables.get_workflow_run_record_table() as table:
                record = table.get_record(table.get_run_record_id(ds, run_id))
                if not record:
                    console.print(
                        f"No workflow for {ds} found with run_id {run_id}",
                        style="bold red",
                    )
        else:
            with settings.tables.get_workflow_run_record_table() as table:
                record = table.get_workflow_run(run_id)
                if not record:
                    console.print(
                        f"No workflow found with run_id {run_id}",
                        style="bold red",
                    )

        return record

    return fetch_record(ctx, _fetch)


@click.command("job")
@click.argument("job_id")
@click.argument("run_id")
@click.pass_context
def fetch_job_cmd(
    ctx: click.Context,
    job_id: str,
    run_id: str,
) -> int:
    """Fetch a job record.

    Outputs the YAML of the record to stdout.
    """

    def _fetch(settings: RecordsSettings, console: Console) -> Optional[JobRunRecord]:
        with settings.tables.get_job_run_record_table() as table:
            record = table.get_record(table.get_run_record_id(run_id, job_id))
            if not record:
                console.print(
                    f"No job for {run_id} found with job_id {job_id}",
                    style="bold red",
                )
            return record

    return fetch_record(ctx, _fetch)


@click.command("task")
@click.argument("job_id")
@click.argument("task_id")
@click.argument("run_id")
@click.pass_context
def fetch_task_cmd(
    ctx: click.Context,
    job_id: str,
    task_id: str,
    run_id: str,
) -> int:
    """Fetch a task record.

    Outputs the YAML of the record to stdout.
    """

    def _fetch(settings: RecordsSettings, console: Console) -> Optional[TaskRunRecord]:
        with settings.tables.get_task_run_record_table() as table:
            record = table.get_record(table.get_run_record_id(run_id, job_id, task_id))
            if not record:
                console.print(
                    f"No task for {run_id} {job_id} found with task_id {task_id}",
                    style="bold red",
                )
            return record

    return fetch_record(ctx, _fetch)


@click.command("logs")
@click.argument("job_id")
@click.argument("task_id")
@click.argument("run_id")
@click.option("-i", "--index", default=-1, help="Index of log to show")
@opt_page
@click.pass_context
def fetch_logs_cmd(
    ctx: click.Context,
    job_id: str,
    task_id: str,
    run_id: str,
    index: int,
    page: bool,
) -> int:
    """Fetch a logfile for a task run.

    Unless paginated, will output the logfile to stdout.
    """

    settings = RecordsSettings.from_context(ctx.obj)
    console = Console(stderr=True)
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
                return NOT_FOUND_EXIT_CODE

        logs = task.log_uris
        if not logs:
            console.print(
                f"No logs for task {job_id}/{task_id} {run_id}",
                style="bold red",
            )
            return NOT_FOUND_EXIT_CODE

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
        cli_output(txt)

    return 0


@click.command("events")
@click.argument("run_id")
@opt_page
@opt_all
@click.pass_context
def fetch_events_cmd(ctx: click.Context, run_id: str, page: bool, all: bool) -> None:
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


@click.group("fetch")
def fetch_cmd() -> None:
    """Fetch a record, logs or events."""
    pass


fetch_cmd.add_command(fetch_workflow_cmd)
fetch_cmd.add_command(fetch_job_cmd)
fetch_cmd.add_command(fetch_task_cmd)
fetch_cmd.add_command(fetch_logs_cmd)
fetch_cmd.add_command(fetch_events_cmd)

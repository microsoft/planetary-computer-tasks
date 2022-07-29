from typing import Callable, Optional, TypeVar

import click
from click.exceptions import Exit
from rich.console import Console
from rich.syntax import Syntax

from pctasks.cli.cli import cli_output
from pctasks.client.client import PCTasksClient
from pctasks.client.errors import NotFoundError
from pctasks.client.records.constants import NOT_FOUND_EXIT_CODE
from pctasks.client.records.context import RecordsCommandContext
from pctasks.client.settings import ClientSettings
from pctasks.client.utils import status_emoji
from pctasks.core.models.api import RecordResponse

T = TypeVar("T", bound=RecordResponse)


def fetch_record(
    ctx: click.Context,
    fetch: Callable[[PCTasksClient, Console], T],
    status_only: bool = False,
) -> int:
    settings = ClientSettings.from_context(ctx.obj)
    client = PCTasksClient(settings)

    records_context: RecordsCommandContext = ctx.obj
    console = Console(stderr=True)

    try:
        record = fetch(client, console)
    except NotFoundError as e:
        console.print(f"[bold red]No record found: {e}")
        raise Exit(NOT_FOUND_EXIT_CODE)

    console.print(
        f"[bold]Status: [/bold]{status_emoji(record.status)} "
        f"{record.status.capitalize()}\n"
    )
    if not status_only:
        if records_context.pretty_print:
            console.print(Syntax(record.to_yaml(), "yaml"))
        else:
            cli_output(record.to_yaml())

    return 0


def fetch_workflow_cmd(
    ctx: click.Context, run_id: str, dataset: Optional[str], status_only: bool = False
) -> int:
    """Fetch a workflow record.

    Outputs the YAML of the record to stdout.
    """
    return fetch_record(
        ctx,
        lambda client, _: client.get_workflow(run_id, dataset),
        status_only=status_only,
    )


def fetch_job_cmd(
    ctx: click.Context,
    run_id: str,
    job_id: str,
) -> int:
    """Fetch a job record.

    Outputs the YAML of the record to stdout.
    """

    return fetch_record(ctx, lambda client, _: client.get_job(run_id, job_id))


def fetch_task_cmd(
    ctx: click.Context,
    run_id: str,
    job_id: str,
    task_id: str,
) -> int:
    """Fetch a task record.

    Outputs the YAML of the record to stdout.
    """

    return fetch_record(ctx, lambda client, _: client.get_task(run_id, job_id, task_id))


def fetch_logs_cmd(
    ctx: click.Context, job_id: str, task_id: str, run_id: str, name: Optional[str]
) -> int:
    """Fetch a task record.

    Outputs the YAML of the record to stdout.
    """

    settings = ClientSettings.from_context(ctx.obj)
    client = PCTasksClient(settings)

    logs = client.get_task_logs(run_id, job_id, task_id, log_name=name)

    console = Console(stderr=True)
    if not logs:
        console.print("[yellow]No logs found.")
        return NOT_FOUND_EXIT_CODE

    console.print(f"[green]Logs for task {task_id}:")

    for log_name, log_text in logs.items():
        console.print(f"\n[bold green]{log_name}:")
        cli_output(log_text)

    return 0

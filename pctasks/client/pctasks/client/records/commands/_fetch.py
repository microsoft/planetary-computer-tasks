from typing import Callable, Optional, TypeVar

import click
from click.exceptions import Exit
from rich.console import Console
from rich.syntax import Syntax

from pctasks.cli.cli import cli_output
from pctasks.client.client import PCTasksClient
from pctasks.client.records.constants import NOT_FOUND_EXIT_CODE
from pctasks.client.records.context import RecordsCommandContext
from pctasks.client.settings import ClientSettings
from pctasks.client.utils import status_emoji
from pctasks.core.models.run import JobPartitionRunRecord, WorkflowRunRecord

T = TypeVar("T", WorkflowRunRecord, JobPartitionRunRecord)


def fetch_run_record(
    ctx: click.Context,
    fetch: Callable[[PCTasksClient, Console], Optional[T]],
    status_only: bool = False,
) -> int:
    settings = ClientSettings.from_context(ctx.obj)
    client = PCTasksClient(settings)

    records_context: RecordsCommandContext = ctx.obj
    console = Console(stderr=True)

    record = fetch(client, console)
    if not record:
        console.print("[bold red]No record found.")
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


def fetch_workflow_cmd(ctx: click.Context, workflow_id: str) -> int:
    """Fetch a workflow run record.

    Outputs the YAML of the record to stdout.
    """
    settings = ClientSettings.from_context(ctx.obj)
    client = PCTasksClient(settings)

    records_context: RecordsCommandContext = ctx.obj
    console = Console(stderr=True)

    record = client.get_workflow(workflow_id)
    if not record:
        console.print("[bold red]No record found.")
        raise Exit(NOT_FOUND_EXIT_CODE)

    if records_context.pretty_print:
        console.print(Syntax(record.to_yaml(), "yaml"))
    else:
        cli_output(record.to_yaml())

    return 0


def fetch_workflow_run_cmd(
    ctx: click.Context, run_id: str, status_only: bool = False
) -> int:
    """Fetch a workflow run record.

    Outputs the YAML of the record to stdout.
    """
    return fetch_run_record(
        ctx,
        lambda client, _: client.get_workflow_run(run_id),
        status_only=status_only,
    )


def fetch_job_part_cmd(
    ctx: click.Context,
    run_id: str,
    job_id: str,
    part_id: str,
    status_only: bool = False,
) -> int:
    """Fetch a job partition run record.

    Outputs the YAML of the record to stdout.
    """

    return fetch_run_record(
        ctx,
        lambda client, _: client.get_job_partition_run(
            run_id, job_id, partition_id=part_id
        ),
        status_only=status_only,
    )


def fetch_task_log_cmd(
    ctx: click.Context,
    run_id: str,
    job_id: str,
    partition_id: str,
    task_id: str,
) -> int:
    """Fetch a task record.

    Outputs the YAML of the record to stdout.
    """

    settings = ClientSettings.from_context(ctx.obj)
    client = PCTasksClient(settings)

    log_text = client.get_task_log(run_id, job_id, partition_id, task_id)

    console = Console(stderr=True)
    if not log_text:
        console.print("[yellow]No logs found.")
        return NOT_FOUND_EXIT_CODE

    console.print(f"\n[bold green]<LOG for task {task_id}>")
    cli_output(log_text)
    console.print("[bold green]</LOG>")

    return 0

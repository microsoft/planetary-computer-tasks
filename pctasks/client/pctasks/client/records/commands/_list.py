from typing import Callable, Iterable, Optional, TypeVar

import click
from click.exceptions import Exit
from rich.console import Console
from rich.table import Table

from pctasks.client.client import PCTasksClient
from pctasks.client.records.constants import NOT_FOUND_EXIT_CODE
from pctasks.client.settings import ClientSettings
from pctasks.client.utils import status_emoji
from pctasks.core.models.run import JobPartitionRunRecord, WorkflowRunRecord

T = TypeVar("T", WorkflowRunRecord, JobPartitionRunRecord)


def list_run_records(
    ctx: click.Context,
    list: Callable[[PCTasksClient, Console], Optional[Iterable[T]]],
) -> int:
    settings = ClientSettings.from_context(ctx.obj)
    client = PCTasksClient(settings)
    console = Console(stderr=True)

    table: Table

    def status_entry(status: str) -> str:
        return f"{status_emoji(status)} {status.capitalize()}"

    def get_table(records: Iterable[T]) -> Table:
        _table = Table()
        _table.add_column("")
        _table.add_column("status")

        for record in records:
            _table.add_row(record.get_id(), status_entry(record.status))

        return _table

    with console.status("Fetching records...") as fetch_status:
        fetch_status.update(
            status="[bold green]Fetching records...",
            spinner="aesthetic",
            spinner_style="green",
        )
        records = list(client, console)
        if records is None:
            console.print("[bold red]No records found.")
            raise Exit(NOT_FOUND_EXIT_CODE)
        table = get_table(records)

    console.print(table)
    return 0


def list_workflows_cmd(ctx: click.Context) -> int:
    """Fetch a workflow run record.

    Outputs the YAML of the record to stdout.
    """
    settings = ClientSettings.from_context(ctx.obj)
    client = PCTasksClient(settings)
    console = Console(stderr=True)

    with console.status("Fetching records...") as fetch_status:
        fetch_status.update(
            status="[bold green]Fetching records...",
            spinner="aesthetic",
            spinner_style="green",
        )
        records = client.list_workflows()
        if records is None:
            console.print("[bold red]No records found.")
            raise Exit(NOT_FOUND_EXIT_CODE)
        table = Table()
        table.add_column("id")
        table.add_column("name")

        for record in records:
            table.add_row(record.get_id(), record.workflow.definition.name)

    console.print(table)
    return 0


def list_workflow_runs_cmd(ctx: click.Context, workflow_id: str) -> int:
    """Fetch a workflow run record.

    Outputs the YAML of the record to stdout.
    """
    return list_run_records(
        ctx,
        lambda client, _: client.list_workflow_runs(workflow_id),
    )


def list_job_part_cmd(
    ctx: click.Context,
    run_id: str,
    job_id: str,
) -> int:
    """Fetch a job partition run record.

    Outputs the YAML of the record to stdout.
    """

    return list_run_records(
        ctx,
        lambda client, _: client.list_job_partition_runs(run_id, job_id),
    )


# def fetch_task_log_cmd(
#     ctx: click.Context,
#     job_id: str,
#     part_id: str,
#     task_id: str,
#     run_id: str,
# ) -> int:
#     """Fetch a task record.

#     Outputs the YAML of the record to stdout.
#     """

#     settings = ClientSettings.from_context(ctx.obj)
#     client = PCTasksClient(settings)

#     log_text = client.get_task_log(run_id, job_id, part_id, task_id)

#     console = Console(stderr=True)
#     if not log_text:
#         console.print("[yellow]No logs found.")
#         return NOT_FOUND_EXIT_CODE

#     console.print(f"[green]Logs for task {task_id}:")

#     console.print(f"\n[bold green]Log for task {task_id}:")
#     cli_output(log_text)

#     return 0

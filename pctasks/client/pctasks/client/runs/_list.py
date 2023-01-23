from typing import Callable, Iterable, Optional, TypeVar

import click
from click.exceptions import Exit
from rich.console import Console
from rich.table import Table

from pctasks.client.client import PCTasksClient
from pctasks.client.constants import NOT_FOUND_EXIT_CODE
from pctasks.client.settings import ClientSettings
from pctasks.client.utils import status_emoji
from pctasks.core.models.run import JobPartitionRunRecord, WorkflowRunRecord

T = TypeVar("T", WorkflowRunRecord, JobPartitionRunRecord)


def list_run_records(
    ctx: click.Context,
    list: Callable[[PCTasksClient, Console], Optional[Iterable[T]]],
    include_timestamp: bool = False,
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
        if include_timestamp:
            _table.add_column("created")

        for record in records:
            assert record.created
            _table.add_row(
                record.get_id(),
                status_entry(record.status),
                record.created.strftime("%Y-%m-%d %H:%M"),
            )

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


def list_workflow_runs_cmd(
    ctx: click.Context,
    workflow_id: str,
    sort_by: Optional[str] = None,
    desc: bool = False,
) -> int:
    """Fetch a workflow run record.

    Outputs the YAML of the record to stdout.
    """
    return list_run_records(
        ctx,
        lambda client, _: client.list_workflow_runs(
            workflow_id, sort_by=sort_by, descending=desc
        ),
        include_timestamp=True,
    )


def list_job_part_cmd(
    ctx: click.Context,
    run_id: str,
    job_id: str,
    sort_by: Optional[str] = None,
    desc: bool = False,
) -> int:
    """Fetch a job partition run record.

    Outputs the YAML of the record to stdout.
    """

    return list_run_records(
        ctx,
        lambda client, _: client.list_job_partition_runs(
            run_id, job_id, sort_by=sort_by, descending=desc
        ),
    )

from typing import Callable, Iterable, Optional, TypeVar

import click
from click.exceptions import Exit
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table

from pctasks.cli.cli import cli_output
from pctasks.client.client import PCTasksClient
from pctasks.client.constants import NOT_FOUND_EXIT_CODE
from pctasks.client.context import ClientCommandContext
from pctasks.client.settings import ClientSettings
from pctasks.client.utils import status_emoji
from pctasks.core.models.run import JobPartitionRunRecord, WorkflowRunRecord

T = TypeVar("T", WorkflowRunRecord, JobPartitionRunRecord)


def cli_list_run_records(
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


def get_run_record(
    ctx: click.Context,
    fetch: Callable[[PCTasksClient, Console], Optional[T]],
    status_only: bool = False,
) -> int:
    settings = ClientSettings.from_context(ctx.obj)
    client = PCTasksClient(settings)

    records_context: ClientCommandContext = ctx.obj
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

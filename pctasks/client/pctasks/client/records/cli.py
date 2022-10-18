import click

from pctasks.client.records.commands.fetch import fetch_cmd
from pctasks.client.records.commands.list import list_cmd
from pctasks.client.records.commands.status import status_cmd


@click.group("records")
@click.option(
    "-p",
    "--pretty-print",
    is_flag=True,
    help="Pretty print output, e.g. syntax highlight YAML",
)
@click.pass_context
def records_cmd(ctx: click.Context, pretty_print: bool) -> None:
    """Query and show records from PCTasks."""
    from . import _cli

    _cli.records_cmd(ctx, pretty_print)


records_cmd.add_command(fetch_cmd)
records_cmd.add_command(list_cmd)
records_cmd.add_command(status_cmd)

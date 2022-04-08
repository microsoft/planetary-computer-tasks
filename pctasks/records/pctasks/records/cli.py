import click

from pctasks.cli.cli import PCTasksCommandContext
from pctasks.records.commands.fetch import fetch_cmd
from pctasks.records.commands.list import list_cmd
from pctasks.records.context import RecordsCommandContext


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
    pctasks_context: PCTasksCommandContext = ctx.obj
    ctx.obj = RecordsCommandContext(
        profile=pctasks_context.profile,
        settings_file=pctasks_context.settings_file,
        pretty_print=pretty_print,
    )


records_cmd.add_command(list_cmd)
records_cmd.add_command(fetch_cmd)

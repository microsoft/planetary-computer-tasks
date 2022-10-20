import click

from pctasks.client.runs.get import get_cmd
from pctasks.client.runs.list import list_cmd
from pctasks.client.runs.status import status_cmd


@click.group("runs")
@click.option(
    "-p",
    "--pretty-print",
    is_flag=True,
    help="Pretty print output, e.g. syntax highlight YAML",
)
@click.pass_context
def runs_cmd(ctx: click.Context, pretty_print: bool) -> None:
    """Query and show records from PCTasks."""
    from pctasks.client.context import ClientCommandContext
    from pctasks.core.context import PCTasksCommandContext

    pctasks_context: PCTasksCommandContext = ctx.obj
    ctx.obj = ClientCommandContext(
        profile=pctasks_context.profile,
        settings_file=pctasks_context.settings_file,
        pretty_print=pretty_print,
    )


runs_cmd.add_command(get_cmd)
runs_cmd.add_command(list_cmd)
runs_cmd.add_command(status_cmd)

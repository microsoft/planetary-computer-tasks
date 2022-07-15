import click

from pctasks.client.records.context import RecordsCommandContext
from pctasks.core.context import PCTasksCommandContext


def records_cmd(ctx: click.Context, pretty_print: bool) -> None:
    """Query and show records from PCTasks."""
    pctasks_context: PCTasksCommandContext = ctx.obj
    ctx.obj = RecordsCommandContext(
        profile=pctasks_context.profile,
        settings_file=pctasks_context.settings_file,
        pretty_print=pretty_print,
    )

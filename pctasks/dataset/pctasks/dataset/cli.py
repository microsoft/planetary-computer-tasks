import click

from pctasks.dataset.chunks.cli import create_chunks_cmd
from pctasks.dataset.items.cli import process_items_cmd


@click.group("dataset")
@click.pass_context
def dataset_cmd(ctx: click.Context) -> None:
    """PCTasks commands for working with datasets."""
    pass


dataset_cmd.add_command(create_chunks_cmd)
dataset_cmd.add_command(process_items_cmd)

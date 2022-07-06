from typing import Optional

import click

from pctasks.cli.cli import PCTasksCommandContext
from pctasks.core.constants import MICROSOFT_OWNER
from pctasks.core.models.dataset import (
    CreateDatasetOperation,
    DatasetIdentifier,
    DatasetOperationSubmitMessage,
)
from pctasks.submit.operations import wait_for_operation
from pctasks.submit.settings import SubmitSettings


def create_dataset(dataset: DatasetIdentifier, settings: SubmitSettings) -> None:
    from pctasks.submit.client import SubmitClient  # cli-perf

    msg = DatasetOperationSubmitMessage(
        operation=CreateDatasetOperation(dataset=dataset)
    )

    with SubmitClient(settings) as submit_client:
        submit_client.submit_operation(msg)

    click.echo(click.style(f"Submitted operation with op ID: {id}", fg="green"))

    # Wait for operation to complete
    def get_dataset() -> Optional[DatasetIdentifier]:
        assert settings.tables
        with settings.tables.get_dataset_table() as table:
            return table.get_dataset(dataset.owner, dataset.name)

    wait_for_operation(get_dataset)


@click.command("create-dataset")
@click.argument("name")
@click.option("-o", "owner", help="Owner of the dataset", default=MICROSOFT_OWNER)
@click.pass_context
def create_cmd(ctx: click.Context, owner: str, name: str = MICROSOFT_OWNER) -> None:
    """Creates a dataset in the system with the given name and owner.

    Can be a local file or a blob URI (e.g. blob://account/container/workflow.yaml)
    """
    context: PCTasksCommandContext = ctx.obj
    settings = SubmitSettings.get(context.profile, context.settings_file)

    if not settings.tables:
        raise click.UsageError("This command requires table settings.")

    dataset = DatasetIdentifier(name=name, owner=owner)

    create_dataset(dataset, settings)


@click.group("dataset")
def dataset_cmd() -> None:
    """Commands for creating and updating datasets."""
    pass


dataset_cmd.add_command(create_cmd)

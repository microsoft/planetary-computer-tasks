import json
import logging
import sys
from typing import Optional

import click

from pctasks.core.models.task import TaskRunMessage
from pctasks.core.storage import get_storage_for_file
from pctasks.task.run import run_task

logger = logging.getLogger(__name__)


@click.command("run")
@click.argument("input_uri")
@click.option(
    "--sas-token",
    default=None,
    help=(
        "A Shared Access Signature (SAS) that can be used "
        "to access input_uris for Azure Blob Storage."
    ),
)
@click.option(
    "--account-url",
    default=None,
    help=(
        "The storage account endpoint. Defaults to the standard "
        "Azure Storage endpoint, but allows integration with e.g. Azurite."
    ),
)
@click.option(
    "-o",
    "--output-uri",
    help="Output URI for the task run. If not supplied, stdout will be used.",
    default=None,
)
@click.option(
    "--output-sas-token",
    help="Token that can be used to write to the output_uri if in Azure Storage.",
    default=None,
)
@click.pass_context
def run_cmd(
    ctx: click.Context,
    input_uri: str,
    sas_token: Optional[str] = None,
    account_url: Optional[str] = None,
    output_uri: Optional[str] = None,
    output_sas_token: Optional[str] = None,
) -> None:
    """Runs a task from a JSON-serialized TaskRUnMessage."""

    storage, path = get_storage_for_file(
        file_uri=input_uri, sas_token=sas_token, account_url=account_url
    )

    msg_text = storage.read_text(path)
    msg = TaskRunMessage.decode(msg_text)

    output = run_task(msg).dict()

    if output_uri:
        output_storage, output_path = get_storage_for_file(
            file_uri=output_uri, sas_token=output_sas_token, account_url=account_url
        )
        output_storage.write_text(output_path, json.dumps(output))
    else:
        sys.stdout.write(json.dumps(output, indent=2))


@click.group("task")
@click.pass_context
def task_cmd(ctx: click.Context) -> None:
    """Commands for running tasks."""
    pass


task_cmd.add_command(run_cmd)

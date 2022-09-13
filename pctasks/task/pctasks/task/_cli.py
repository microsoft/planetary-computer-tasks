import logging
import sys
from typing import Optional

import click

from pctasks.core.models.task import TaskRunMessage
from pctasks.core.storage import get_storage_for_file
from pctasks.task.run import run_task

logger = logging.getLogger(__name__)


def run_cmd(
    ctx: click.Context,
    input_uri: str,
    sas_token: Optional[str] = None,
    account_url: Optional[str] = None,
    output_uri: Optional[str] = None,
    output_sas_token: Optional[str] = None,
) -> None:
    """Runs a task from a JSON-serialized TaskRunMessage."""

    storage, path = get_storage_for_file(
        file_uri=input_uri, sas_token=sas_token, account_url=account_url
    )

    msg_text = storage.read_text(path)
    msg = TaskRunMessage.decode(msg_text)

    try:
        output = run_task(msg)

        if output_uri:
            logger.info("Saving task output...")
            output_storage, output_path = get_storage_for_file(
                file_uri=output_uri, sas_token=output_sas_token, account_url=account_url
            )
            output_storage.write_text(output_path, output.json())
            logger.info("...output saved")
        else:
            sys.stdout.write(output.json(indent=2))
    finally:
        logger.info("Task run complete.")

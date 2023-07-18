import logging
import os
import sys
from typing import Optional

import click

from pctasks.core.models.task import TaskRunMessage
from pctasks.core.storage import get_storage_for_file
from pctasks.core.storage.blob import ClientSecretCredentials
from pctasks.task.constants import (
    TASKIO_CLIENT_ID_ENV_VAR,
    TASKIO_CLIENT_SECRET_ENV_VAR,
    TASKIO_TENANT_ID_ENV_VAR,
)
from pctasks.task.run import run_task

logger = logging.getLogger(__name__)


def get_taskio_credentials() -> Optional[ClientSecretCredentials]:
    # Variables to store the values of the environment variables
    taskio_tenant_id: Optional[str] = os.getenv(TASKIO_TENANT_ID_ENV_VAR)
    taskio_client_id: Optional[str] = os.getenv(TASKIO_CLIENT_ID_ENV_VAR)
    taskio_client_secret: Optional[str] = os.getenv(TASKIO_CLIENT_SECRET_ENV_VAR)

    # Check if any of the environment variables is set
    if taskio_tenant_id or taskio_client_id or taskio_client_secret:
        # Require that all three are set
        if not taskio_tenant_id or not taskio_client_id or not taskio_client_secret:
            raise ValueError("All three environment variables must be set")
        else:
            return ClientSecretCredentials(
                tenant_id=taskio_tenant_id,
                client_id=taskio_client_id,
                client_secret=taskio_client_secret,
            )
    return None


def run_cmd(
    ctx: click.Context,
    input_uri: str,
    sas_token: Optional[str] = None,
    account_url: Optional[str] = None,
    output_uri: Optional[str] = None,
    output_sas_token: Optional[str] = None,
) -> None:
    """Runs a task from a JSON-serialized TaskRunMessage."""

    logger.info("Loading taskio credentials")
    taskio_credentials = get_taskio_credentials()

    storage, path = get_storage_for_file(
        file_uri=input_uri,
        sas_token=sas_token,
        account_url=account_url,
        client_secret_credentials=taskio_credentials,
    )

    msg_text = storage.read_text(path)
    msg = TaskRunMessage.decode(msg_text)
    logger.info("Got task run message")

    try:
        output = run_task(msg)

        if output_uri:
            logger.info("Saving task output...")
            output_storage, output_path = get_storage_for_file(
                file_uri=output_uri,
                sas_token=output_sas_token,
                account_url=account_url,
                client_secret_credentials=taskio_credentials,
            )
            output_storage.write_text(output_path, output.json())
            logger.info("...output saved")
        else:
            sys.stdout.write(output.json(indent=2))
    finally:
        logger.info("Task run complete.")

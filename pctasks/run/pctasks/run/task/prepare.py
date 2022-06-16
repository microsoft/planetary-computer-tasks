import logging
import os
from datetime import datetime, timedelta

from azure.core.credentials import AzureNamedKeyCredential
from azure.data.tables import TableSasPermissions, generate_table_sas
from azure.storage.blob import BlobSasPermissions, generate_blob_sas

from pctasks.core.constants import ENV_VAR_TASK_APPINSIGHTS_KEY
from pctasks.core.models.config import BlobConfig, ImageConfig, TableSasConfig
from pctasks.core.models.task import TaskRunConfig, TaskRunMessage
from pctasks.core.models.tokens import StorageAccountTokens
from pctasks.core.storage.blob import BlobStorage, BlobUri
from pctasks.run.models import PreparedTaskSubmitMessage, TaskSubmitMessage
from pctasks.run.secrets.base import SecretsProvider
from pctasks.run.secrets.keyvault import KeyvaultSecretsProvider
from pctasks.run.secrets.local import LocalSecretsProvider
from pctasks.run.settings import RunSettings
from pctasks.run.utils import (
    get_run_log_path,
    get_task_input_path,
    get_task_output_path,
)

logger = logging.getLogger(__name__)


def write_task_run_msg(run_msg: TaskRunMessage, settings: RunSettings) -> BlobConfig:
    """
    Write the task run message to the Task IO input file

    Returns a SAS token that can be used to read the table.
    """
    task_input_path = get_task_input_path(
        job_id=run_msg.config.job_id,
        task_id=run_msg.config.task_id,
        run_id=run_msg.config.run_id,
    )
    task_input_uri = BlobUri(
        f"blob://{settings.blob_account_name}/"
        f"{settings.task_io_blob_container}/"
        f"{task_input_path}"
    )

    task_io_storage = BlobStorage.from_account_key(
        f"blob://{task_input_uri.storage_account_name}/{task_input_uri.container_name}",
        account_key=settings.blob_account_key,
        account_url=settings.blob_account_url,
    )

    task_io_storage.write_text(
        task_input_path,
        run_msg.encoded(),
    )

    input_blob_sas_token = generate_blob_sas(
        account_name=settings.blob_account_name,
        account_key=settings.blob_account_key,
        container_name=settings.task_io_blob_container,
        blob_name=task_input_path,
        start=datetime.now(),
        expiry=datetime.utcnow() + timedelta(hours=24 * 7),
        permission=BlobSasPermissions(read=True),
    )

    return BlobConfig(
        uri=str(task_input_uri),
        sas_token=input_blob_sas_token,
        account_url=settings.blob_account_url,
    )


def prepare_task(
    submit_msg: TaskSubmitMessage,
    run_id: str,
    settings: RunSettings,
) -> PreparedTaskSubmitMessage:
    """
    Prepare a task to be run by an Executor.

    This includes:
    - translate image-key to image and configured environment, tags
    - inject secrets
    - configure task IO, logging, and records access
    - write task run message to task IO input file
    """
    if not submit_msg.instance_id:
        raise ValueError("submit_msg.instance_id is required")

    target_environment = submit_msg.target_environment
    job_id = submit_msg.job_id
    task_config = submit_msg.config
    task_id = task_config.id

    event_logger_app_insights_key = os.environ.get(ENV_VAR_TASK_APPINSIGHTS_KEY)

    environment = submit_msg.config.environment
    task_tags = submit_msg.config.tags

    # --Handle image key--

    if not task_config.image:
        image_key = task_config.image_key
        if not image_key:
            # Should have been handled by model validation
            raise ValueError("Must specify either image_key or image.")

        logger.info(f"No image specified, using image key '{image_key}'")

        with settings.get_image_key_table() as image_key_table:
            image_config = image_key_table.get_image(image_key, target_environment)

        if image_config is None:
            raise ValueError(
                f"Image for image key '{image_key}' and target environment "
                f"'{target_environment}' not found "
                f"in table {settings.image_key_table_name}."
            )

        # Merge the environment variables from the image-key table into
        # this environment. Explicit environment takes precedence.
        if environment:
            if image_config.environment:
                logger.info(
                    "Merging environment from image key table "
                    "into submit msg environment."
                )
                environment = {
                    **(image_config.get_environment() or {}),
                    **environment,
                }
        else:
            logger.info("Setting image key environment as task environment.")
            environment = image_config.get_environment()

        # Merge the tags from the image-key table into
        # the message tags. Explicit tags takes precedence.
        if task_tags:
            if image_config.environment:
                logger.info(
                    "Merging tags from image key table " "into submit msg tags."
                )
                task_tags = {
                    **(image_config.get_tags() or {}),
                    **task_tags,
                }
        else:
            logger.info("Setting image key tags as task tags.")
            task_tags = image_config.get_tags()
    else:
        image_config = ImageConfig(image=task_config.image)

    # --Handle secrets--

    secrets_provider: SecretsProvider
    if settings.local_secrets:
        secrets_provider = LocalSecretsProvider()
    else:
        assert settings.keyvault_url  # Handled by model validation
        secrets_provider = KeyvaultSecretsProvider.get_provider(
            settings.keyvault_url,
            tenant_id=settings.keyvault_sp_tenant_id or None,
            client_id=settings.keyvault_sp_client_id or None,
            client_secret=settings.keyvault_sp_client_secret or None,
        )

    with secrets_provider:
        if environment:
            environment = secrets_provider.substitute_secrets(environment)

        tokens = submit_msg.tokens
        if tokens:
            tokens = {
                account: StorageAccountTokens(
                    **secrets_provider.substitute_secrets(v.dict())
                )
                for account, v in tokens.items()
            }

    # --Handle configuration--

    # Tables

    tables_cred = AzureNamedKeyCredential(
        name=settings.tables_account_name, key=settings.tables_account_key
    )

    task_runs_table_sas_token = generate_table_sas(
        credential=tables_cred,
        table_name=settings.task_run_record_table_name,
        start=datetime.now(),
        expiry=datetime.utcnow() + timedelta(hours=24 * 7),
        permission=TableSasPermissions(read=True, write=True, update=True),
    )

    task_runs_table_config = TableSasConfig(
        account_url=settings.tables_account_url,
        table_name=settings.task_run_record_table_name,
        sas_token=task_runs_table_sas_token,
    )

    # Blob
    log_path = get_run_log_path(job_id, task_id, run_id)
    log_uri = (
        f"blob://{settings.blob_account_name}/{settings.log_blob_container}/{log_path}"
    )
    log_blob_sas_token = generate_blob_sas(
        account_name=settings.blob_account_name,
        account_key=settings.blob_account_key,
        container_name=settings.log_blob_container,
        blob_name=log_path,
        start=datetime.now(),
        expiry=datetime.utcnow() + timedelta(hours=24 * 7),
        permission=BlobSasPermissions(write=True),
    )
    log_blob_config = BlobConfig(
        uri=log_uri, sas_token=log_blob_sas_token, account_url=settings.blob_account_url
    )

    output_path = get_task_output_path(job_id, task_id, run_id)
    output_uri = (
        f"blob://{settings.blob_account_name}/"
        f"{settings.task_io_blob_container}/{output_path}"
    )
    output_blob_sas_token = generate_blob_sas(
        account_name=settings.blob_account_name,
        account_key=settings.blob_account_key,
        container_name=settings.task_io_blob_container,
        blob_name=output_path,
        start=datetime.now(),
        expiry=datetime.utcnow() + timedelta(hours=24 * 7),
        permission=BlobSasPermissions(write=True),
    )
    output_blob_config = BlobConfig(
        uri=output_uri,
        sas_token=output_blob_sas_token,
        account_url=settings.blob_account_url,
    )

    config = TaskRunConfig(
        image=image_config.image,
        run_id=submit_msg.run_id,
        job_id=submit_msg.job_id,
        task_id=submit_msg.config.id,
        task=task_config.task,
        environment=environment,
        tokens=tokens,
        task_runs_table_config=task_runs_table_config,
        output_blob_config=output_blob_config,
        log_blob_config=log_blob_config,
        event_logger_app_insights_key=event_logger_app_insights_key,
    )

    run_msg = TaskRunMessage(args=task_config.args, config=config)

    task_input_blob_config = write_task_run_msg(run_msg, settings)

    return PreparedTaskSubmitMessage(
        task_submit_message=submit_msg,
        task_run_message=run_msg,
        task_input_blob_config=task_input_blob_config,
        task_tags=task_tags,
    )

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from azure.storage.blob import BlobSasPermissions, generate_blob_sas

from pctasks.core.constants import ENV_VAR_TASK_APPINSIGHTS_KEY
from pctasks.core.models.config import BlobConfig
from pctasks.core.models.task import TaskDefinition, TaskRunConfig, TaskRunMessage
from pctasks.core.models.tokens import StorageAccountTokens
from pctasks.core.storage.blob import BlobStorage, BlobUri, generate_key_for_sas
from pctasks.core.utils.backoff import with_backoff
from pctasks.core.utils.template import PCTemplater
from pctasks.run.errors import TaskPreparationError
from pctasks.run.models import (
    PreparedTaskData,
    PreparedTaskSubmitMessage,
    TaskSubmitMessage,
)
from pctasks.run.secrets.base import SecretsProvider
from pctasks.run.secrets.keyvault import KeyvaultSecretsProvider
from pctasks.run.secrets.local import LocalSecretsProvider
from pctasks.run.settings import RunSettings
from pctasks.run.task.base import TaskRunner
from pctasks.run.utils import (
    get_task_input_path,
    get_task_log_path,
    get_task_output_path,
    get_task_status_path,
)

logger = logging.getLogger(__name__)


def prepare_task_data(
    dataset_id: str,
    run_id: str,
    job_id: str,
    task_def: TaskDefinition,
    settings: RunSettings,
    tokens: Optional[Dict[str, StorageAccountTokens]],
    target_environment: Optional[str],
    task_runner: Optional[TaskRunner] = None,
) -> PreparedTaskData:
    environment = task_def.environment
    task_tags = task_def.tags

    # --Handle image key--

    if not task_def.image:
        image_key = task_def.image_key
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

        image = image_config.image

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
        image = task_def.image

    # --Handle secrets--

    secrets_provider: SecretsProvider
    if settings.local_secrets:
        secrets_provider = LocalSecretsProvider(settings)
    else:
        secrets_provider = KeyvaultSecretsProvider.get_provider(settings)

    with secrets_provider:
        if environment:
            environment = secrets_provider.substitute_secrets(environment)

        if tokens:

            def _transform_tokens(tokens: Dict[str, Any]) -> Dict[str, Any]:
                tks = secrets_provider.substitute_secrets(tokens)
                try:
                    tks = with_backoff(lambda: PCTemplater().template_dict(tks))
                except Exception as e:
                    raise TaskPreparationError(
                        f"Failed to fetch SAS tokens from the Planetary Computer: {e}"
                    ) from e
                return tks

            tokens = {
                account: StorageAccountTokens(**_transform_tokens(tokens=v.dict()))
                for account, v in tokens.items()
            }

    runner_info: Optional[Dict[str, Any]] = None
    if task_runner:
        runner_info = task_runner.prepare_task_info(
            dataset_id, run_id, job_id, task_def, image, task_tags
        )

    return PreparedTaskData(
        image=image,
        environment=environment,
        tags=task_tags,
        tokens=tokens,
        runner_info=runner_info or {},
    )


def write_task_run_msg(run_msg: TaskRunMessage, settings: RunSettings) -> BlobConfig:
    """
    Write the task run message to the Task IO input file

    Returns a SAS token that can be used to read the table.
    """
    task_input_path = get_task_input_path(
        job_id=run_msg.config.job_id,
        partition_id=run_msg.config.partition_id,
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

    credential_options = generate_key_for_sas(
        settings.blob_account_url, settings.blob_account_key
    )
    input_blob_sas_token = generate_blob_sas(
        account_name=settings.blob_account_name,
        container_name=settings.task_io_blob_container,
        blob_name=task_input_path,
        start=datetime.utcnow(),
        expiry=datetime.utcnow() + timedelta(hours=24 * 7),
        permission=BlobSasPermissions(read=True),
        **credential_options,
    )

    return BlobConfig(
        uri=str(task_input_uri),
        sas_token=input_blob_sas_token,
        account_url=settings.blob_account_url,
    )


def prepare_task(
    submit_msg: TaskSubmitMessage,
    run_id: str,
    task_data: PreparedTaskData,
    settings: RunSettings,
    generate_sas_tokens: bool = True,
) -> PreparedTaskSubmitMessage:
    """
    Prepare a task to be run by an Executor.

    This includes:
    - translate image-key to image and configured environment, tags
    - inject secrets
    - configure task IO, logging, and records access
    - write task run message to task IO input file

    Parameters
    ----------
    generate_sas_tokens: bool, default True
        Whether to generate SAS tokens for each operation that needs to
        read from or write to Blob Storage. ``generate_sas_tokens=False``,
        the process running the task will need some other way to access
        the necessary blob storage resources (e.g. a managed identity or
        environment credentials).
    """
    job_id = submit_msg.job_id
    partition_id = submit_msg.partition_id
    task_def = submit_msg.definition
    task_id = task_def.id

    event_logger_app_insights_key = os.environ.get(ENV_VAR_TASK_APPINSIGHTS_KEY)

    # --Handle configuration--

    # Handle status blob

    task_status_path = get_task_status_path(job_id, partition_id, task_id, run_id)
    task_status_uri = (
        f"blob://{settings.blob_account_name}/"
        f"{settings.task_io_blob_container}/{task_status_path}"
    )
    credential_options = generate_key_for_sas(
        settings.blob_account_url, settings.blob_account_key
    )
    if generate_sas_tokens:
        log_blob_sas_token = generate_blob_sas(
            account_name=settings.blob_account_name,
            container_name=settings.task_io_blob_container,
            blob_name=task_status_path,
            start=datetime.utcnow(),
            expiry=datetime.utcnow() + timedelta(hours=24 * 7),
            permission=BlobSasPermissions(write=True),
            **credential_options,
        )
    else:
        log_blob_sas_token = None

    status_blob_config = BlobConfig(
        uri=task_status_uri,
        sas_token=log_blob_sas_token,
        account_url=settings.blob_account_url,
    )

    # Handle log blob
    log_path = get_task_log_path(job_id, partition_id, task_id, run_id)
    log_uri = (
        f"blob://{settings.blob_account_name}/{settings.log_blob_container}/{log_path}"
    )
    if generate_sas_tokens:
        credential_options = generate_key_for_sas(
            settings.blob_account_url, settings.blob_account_key
        )
        log_blob_sas_token = generate_blob_sas(
            account_name=settings.blob_account_name,
            container_name=settings.log_blob_container,
            blob_name=log_path,
            start=datetime.utcnow(),
            expiry=datetime.utcnow() + timedelta(hours=24 * 7),
            permission=BlobSasPermissions(write=True),
            **credential_options,
        )
    else:
        log_blob_sas_token = None
    log_blob_config = BlobConfig(
        uri=log_uri, sas_token=log_blob_sas_token, account_url=settings.blob_account_url
    )

    # Handle output blob

    output_path = get_task_output_path(job_id, partition_id, task_id, run_id)
    output_uri = (
        f"blob://{settings.blob_account_name}/"
        f"{settings.task_io_blob_container}/{output_path}"
    )
    if generate_sas_tokens:
        credential_options = generate_key_for_sas(
            settings.blob_account_url, settings.blob_account_key
        )
        output_blob_sas_token = generate_blob_sas(
            account_name=settings.blob_account_name,
            container_name=settings.task_io_blob_container,
            blob_name=output_path,
            start=datetime.utcnow(),
            expiry=datetime.utcnow() + timedelta(hours=24 * 7),
            permission=BlobSasPermissions(write=True),
            **credential_options,
        )
    else:
        output_blob_sas_token = None

    output_blob_config = BlobConfig(
        uri=output_uri,
        sas_token=output_blob_sas_token,
        account_url=settings.blob_account_url,
    )

    # Handle code config
    code_src_blob_config: Optional[BlobConfig] = None
    code_requirements_blob_config: Optional[BlobConfig] = None
    code_pip_options: Optional[List[str]] = None

    code_config = task_def.code
    if code_config:
        code_uri = code_config.src
        code_path = code_config.get_src_path()
        if generate_sas_tokens:
            credential_options = generate_key_for_sas(
                settings.blob_account_url, settings.blob_account_key
            )
            code_blob_sas_token = generate_blob_sas(
                account_name=settings.blob_account_name,
                container_name=settings.code_blob_container,
                blob_name=code_path,
                start=datetime.utcnow(),
                expiry=datetime.utcnow() + timedelta(hours=24 * 7),
                permission=BlobSasPermissions(read=True),
                **credential_options,
            )
        else:
            code_blob_sas_token = None

        code_src_blob_config = BlobConfig(
            uri=code_uri,
            sas_token=code_blob_sas_token,
            account_url=settings.blob_account_url,
        )

        requirements_uri = code_config.requirements
        if requirements_uri:
            requirements_path = code_config.get_requirements_path()
            if not requirements_path:
                # Should be caught by model validation
                raise ValueError(f"Invalid requirements URI: {code_uri}")

            if generate_sas_tokens:
                credential_options = generate_key_for_sas(
                    settings.blob_account_url, settings.blob_account_key
                )
                requirements_blob_sas_token = generate_blob_sas(
                    account_name=settings.blob_account_name,
                    container_name=settings.code_blob_container,
                    blob_name=requirements_path,
                    start=datetime.utcnow(),
                    expiry=datetime.utcnow() + timedelta(hours=24 * 7),
                    permission=BlobSasPermissions(read=True),
                    **credential_options,
                )
            else:
                requirements_blob_sas_token = None
            code_requirements_blob_config = BlobConfig(
                uri=requirements_uri,
                sas_token=requirements_blob_sas_token,
                account_url=settings.blob_account_url,
            )

        code_pip_options = code_config.pip_options

    config = TaskRunConfig(
        image=task_data.image,
        run_id=run_id,
        job_id=job_id,
        partition_id=partition_id,
        task_id=task_id,
        task=task_def.task,
        environment=task_data.environment,
        tokens=task_data.tokens,
        status_blob_config=status_blob_config,
        output_blob_config=output_blob_config,
        log_blob_config=log_blob_config,
        code_src_blob_config=code_src_blob_config,
        code_requirements_blob_config=code_requirements_blob_config,
        code_pip_options=code_pip_options,
        event_logger_app_insights_key=event_logger_app_insights_key,
    )

    run_msg = TaskRunMessage(args=task_def.args, config=config)

    task_input_blob_config = write_task_run_msg(run_msg, settings)

    return PreparedTaskSubmitMessage(
        task_submit_message=submit_msg,
        task_run_message=run_msg,
        task_input_blob_config=task_input_blob_config,
        task_data=task_data,
    )

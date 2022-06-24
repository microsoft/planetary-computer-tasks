import logging
from typing import Optional

import click
from strictyaml.exceptions import MarkedYAMLError

from pctasks.cli.cli import PCTasksCommandContext, cli_output, cli_print
from pctasks.core.models.workflow import (
    JobConfig,
    WorkflowConfig,
    WorkflowSubmitMessage,
)
from pctasks.core.yaml import YamlValidationError
from pctasks.dataset.constants import DEFAULT_DATASET_YAML_PATH
from pctasks.dataset.splits.models import CreateSplitsOptions, CreateSplitsTaskConfig
from pctasks.dataset.template import template_dataset_file
from pctasks.dataset.utils import opt_collection, opt_ds_config, opt_submit
from pctasks.submit.client import SubmitClient
from pctasks.submit.settings import SubmitSettings

logger = logging.getLogger(__name__)


@click.command("create-splits")
@opt_ds_config
@opt_collection
@click.option("--limit", type=int, help="Limit prefix linking, used for testing")
@opt_submit
@click.pass_context
def create_splits_cmd(
    ctx: click.Context,
    dataset: Optional[str] = None,
    collection: Optional[str] = None,
    limit: Optional[int] = None,
    submit: bool = False,
) -> None:
    """Creates a chunkset for bulk processing."""
    context: PCTasksCommandContext = ctx.obj
    try:
        ds_config = template_dataset_file(dataset)
    except (MarkedYAMLError, YamlValidationError) as e:
        raise click.ClickException(f"Invalid dataset config.\n{e}")
    except FileNotFoundError:
        raise click.ClickException(
            "No dataset config found. Use --config to specify "
            f"or name your config {DEFAULT_DATASET_YAML_PATH}."
        )

    if not ds_config:
        raise click.ClickException("No dataset config found.")

    collection_config = ds_config.get_collection(collection)

    task_config = CreateSplitsTaskConfig.from_collection(
        ds_config, collection_config, options=CreateSplitsOptions(limit=limit)
    )

    workflow = WorkflowConfig(
        name=f"Create splits for {collection_config.id}",
        dataset=ds_config.get_identifier(),
        collection_id=collection_config.id,
        image=ds_config.image,
        tokens=collection_config.get_tokens(),
        jobs={"splits": JobConfig(tasks=[task_config])},
    )

    submit_message = WorkflowSubmitMessage(workflow=workflow)

    if not submit:
        cli_output(submit_message.to_yaml())
    else:
        settings = SubmitSettings.get(context.profile, context.settings_file)
        client = SubmitClient(settings)
        cli_print(click.style(f"  Submitting {submit_message.run_id}...", fg="green"))
        client.submit_workflow(submit_message)

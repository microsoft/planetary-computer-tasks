import logging
from typing import List, Optional, Tuple

import click
from strictyaml.exceptions import MarkedYAMLError

from pctasks.client.workflow.commands import cli_handle_workflow
from pctasks.client.workflow.options import opt_args
from pctasks.core.models.workflow import JobDefinition, WorkflowDefinition
from pctasks.core.yaml import YamlValidationError
from pctasks.dataset.constants import DEFAULT_DATASET_YAML_PATH
from pctasks.dataset.splits.models import CreateSplitsOptions, CreateSplitsTaskConfig
from pctasks.dataset.template import template_dataset_file
from pctasks.dataset.utils import opt_collection, opt_ds_config, opt_submit, opt_upsert

logger = logging.getLogger(__name__)


@click.command("create-splits")  # type: ignore[arg-type]
@opt_ds_config
@opt_collection
@click.option("--limit", type=int, help="Limit prefix linking, used for testing")
@opt_args
@opt_submit
@opt_upsert
@click.pass_context
def create_splits_cmd(
    ctx: click.Context,
    dataset: Optional[str] = None,
    collection: Optional[str] = None,
    limit: Optional[int] = None,
    arg: List[Tuple[str, str]] = [],
    upsert: bool = False,
    submit: bool = False,
) -> None:
    """Creates a chunkset for bulk processing."""
    if submit and not upsert:
        raise click.UsageError("Cannot submit without --upsert")

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

    workflow_id = f"{ds_config.id}-{collection_config.id}-create-splits"
    workflow_def = WorkflowDefinition(
        id=workflow_id,
        name=f"Create splits for {collection_config.id}",
        dataset=ds_config.id,
        collection_id=collection_config.id,
        image=ds_config.image,
        tokens=collection_config.get_tokens(),
        jobs={"splits": JobDefinition(tasks=[task_config])},
    )

    cli_handle_workflow(
        ctx,
        workflow_def,
        upsert=upsert,
        upsert_and_submit=submit,
        args={a[0]: a[1] for a in arg},
    )

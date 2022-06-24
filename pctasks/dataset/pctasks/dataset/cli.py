import logging
from typing import Optional

import click
from pystac.utils import str_to_datetime
from strictyaml.exceptions import MarkedYAMLError

from pctasks.cli.cli import PCTasksCommandContext, cli_output, cli_print
from pctasks.core.models.workflow import WorkflowSubmitMessage
from pctasks.core.utils import map_opt
from pctasks.core.yaml import YamlValidationError
from pctasks.dataset.chunks.models import ChunkOptions
from pctasks.dataset.constants import DEFAULT_DATASET_YAML_PATH
from pctasks.dataset.splits.models import CreateSplitsOptions
from pctasks.dataset.template import template_dataset_file
from pctasks.dataset.utils import opt_collection, opt_ds_config, opt_submit
from pctasks.dataset.workflow import (
    create_chunks_workflow,
    create_process_items_workflow,
)
from pctasks.submit.client import SubmitClient
from pctasks.submit.settings import SubmitSettings

logger = logging.getLogger(__name__)


@click.group("dataset")
@click.pass_context
def dataset_cmd(ctx: click.Context) -> None:
    """PCTasks commands for working with datasets."""
    pass


@click.command("create-chunks")
@click.argument("chunkset_id")
@opt_ds_config
@opt_collection
@click.option(
    "-s",
    "--since",
    help=("Only process files that have been modified at or after this datetime."),
)
@click.option("--limit", type=int, help="Limit prefix listing, used for testing")
@opt_submit
@click.pass_context
def create_chunks_cmd(
    ctx: click.Context,
    chunkset_id: str,
    dataset: Optional[str] = None,
    collection: Optional[str] = None,
    since: Optional[str] = None,
    limit: Optional[int] = None,
    submit: bool = False,
) -> None:
    """Creates asset chunks for bulk processing."""
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

    workflow = create_chunks_workflow(
        dataset=ds_config,
        collection=collection_config,
        chunkset_id=chunkset_id,
        create_splits_options=CreateSplitsOptions(limit=limit),
        chunk_options=ChunkOptions(since=map_opt(str_to_datetime, since)),
    )

    if not submit:
        cli_output(workflow.to_yaml())
    else:
        submit_message = WorkflowSubmitMessage(workflow=workflow)
        settings = SubmitSettings.get(context.profile, context.settings_file)
        client = SubmitClient(settings)
        cli_print(click.style(f"  Submitting {submit_message.run_id}...", fg="green"))
        client.submit_workflow(submit_message)


@click.command("process-items")
@click.argument("chunkset_id")
@opt_ds_config
@opt_collection
@click.option(
    "-t",
    "--target",
    help="The target environment to process the items in.",
)
@click.option("--limit", type=int, help="Limit, used for testing")
@click.option("--no-ingest", is_flag=True, help="Create ndjsons, but don't ingest.")
@click.option(
    "-e",
    "--use-existing-chunks",
    is_flag=True,
    help="Process existing chunkset, do not recreate.",
)
@click.option(
    "-s",
    "--since",
    help=("Only process files that have been modified at or after this datetime."),
)
@opt_submit
@click.pass_context
def process_items_cmd(
    ctx: click.Context,
    chunkset_id: str,
    dataset: Optional[str],
    collection: Optional[str],
    target: str,
    no_ingest: bool = False,
    use_existing_chunks: bool = False,
    since: Optional[str] = None,
    limit: Optional[int] = None,
    submit: bool = False,
) -> None:
    """Create and ingest items.

    Read the asset paths from the chunk file at CHUNK and
    submit a workflow to process into items and ingest into
    the database.
    """
    context: PCTasksCommandContext = ctx.obj
    try:
        ds_config = template_dataset_file(dataset)
    except (MarkedYAMLError, YamlValidationError) as e:
        raise click.ClickException(f"Invalid dataset config.\n{e}")
    except FileNotFoundError:
        raise click.ClickException(
            "No dataset config found. Use --dataset to specify "
            f"or name your config {DEFAULT_DATASET_YAML_PATH}."
        )
    if not ds_config:
        raise click.ClickException("No dataset config found.")

    collection_config = ds_config.get_collection(collection)

    workflow = create_process_items_workflow(
        dataset=ds_config,
        collection=collection_config,
        chunkset_id=chunkset_id,
        use_existing_chunks=use_existing_chunks,
        ingest=not no_ingest,
        create_splits_options=CreateSplitsOptions(limit=limit),
        chunk_options=ChunkOptions(since=map_opt(str_to_datetime, since), limit=limit),
        create_items_options=None,
        ingest_options=None,
        target=target,
        tags=None,
    )

    if not submit:
        cli_output(workflow.to_yaml())
    else:
        submit_message = WorkflowSubmitMessage(workflow=workflow)
        settings = SubmitSettings.get(context.profile, context.settings_file)
        client = SubmitClient(settings)
        cli_print(click.style(f"  Submitting {submit_message.run_id}...", fg="green"))
        client.submit_workflow(submit_message)


dataset_cmd.add_command(create_chunks_cmd)
dataset_cmd.add_command(process_items_cmd)

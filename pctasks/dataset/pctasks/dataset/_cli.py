import logging
from typing import List, Optional, Tuple

import click
from pystac.utils import str_to_datetime
from strictyaml.exceptions import MarkedYAMLError

from pctasks.cli.cli import cli_output, cli_print
from pctasks.client.workflow.commands import cli_handle_workflow
from pctasks.core.utils import map_opt
from pctasks.core.yaml import YamlValidationError
from pctasks.dataset.chunks.models import ChunkOptions
from pctasks.dataset.constants import DEFAULT_DATASET_YAML_PATH
from pctasks.dataset.models import (
    MultipleCollectionsError,
    DatasetDefinition,
    CollectionDefinition,
)
from pctasks.dataset.splits.models import CreateSplitsOptions
from pctasks.dataset.template import template_dataset_file
from pctasks.dataset.workflow import (
    create_chunks_workflow,
    create_ingest_collection_workflow,
    create_process_items_workflow,
    create_reprocess_chunkset_workflow,
)

logger = logging.getLogger(__name__)


def _handle_multiple_collections(e: MultipleCollectionsError) -> Exception:
    cli_print("[bold yellow]Multiple Collections Found[/bold yellow]:")
    for c in e.collection_ids:
        cli_print(f" - {c}")
    return click.UsageError("Please specify which collection using --collection")


def create_chunks_cmd(
    ctx: click.Context,
    chunkset_id: str,
    dataset: Optional[str] = None,
    collection: Optional[str] = None,
    arg: List[Tuple[str, str]] = [],
    since: Optional[str] = None,
    limit: Optional[int] = None,
    submit: bool = False,
    upsert: bool = False,
    target: Optional[str] = None,
    workflow_id: Optional[str] = None,
) -> None:
    """Creates workflow to generate asset chunks for bulk processing.

    Output: If -s is present, will print the run ID to stdout. Otherwise,
    will print the workflow yaml.
    """
    try:
        ds_config = template_dataset_file(dataset, dict(arg))
    except (MarkedYAMLError, YamlValidationError) as e:
        raise click.ClickException(f"Invalid dataset config.\n{e}")
    except FileNotFoundError:
        raise click.ClickException(
            "No dataset config found. Use --config to specify "
            f"or name your config {DEFAULT_DATASET_YAML_PATH}."
        )

    if not ds_config:
        raise click.ClickException("No dataset config found.")

    try:
        collection_config = ds_config.get_collection(collection)
    except MultipleCollectionsError as e:
        raise _handle_multiple_collections(e)

    workflow_def = create_chunks_workflow(
        dataset=ds_config,
        collection=collection_config,
        chunkset_id=chunkset_id,
        create_splits_options=CreateSplitsOptions(limit=limit),
        chunk_options=ChunkOptions(since=map_opt(str_to_datetime, since)),
        target=target,
    )

    cli_handle_workflow(
        ctx,
        workflow_def,
        workflow_id=workflow_id,
        upsert=upsert,
        upsert_and_submit=submit,
        args={a[0]: a[1] for a in arg},
    )


def _configs_from_cli(
    dataset: Optional[str], arg: List[Tuple[str, str]], collection: Optional[str]
) -> Tuple[DatasetDefinition, CollectionDefinition]:
    try:
        ds_config = template_dataset_file(dataset, dict(arg))
    except (MarkedYAMLError, YamlValidationError) as e:
        raise click.ClickException(f"Invalid dataset config.\n{e}")
    except FileNotFoundError:
        raise click.ClickException(
            "No dataset config found. Use --dataset to specify "
            f"or name your config {DEFAULT_DATASET_YAML_PATH}."
        )
    if not ds_config:
        raise click.ClickException("No dataset config found.")

    try:
        collection_config = ds_config.get_collection(collection)
    except MultipleCollectionsError as e:
        raise _handle_multiple_collections(e)
    return ds_config, collection_config


def reprocess_chunkset_cmd(
    ctx: click.Context,
    chunk_id: str,
    asset_uri: str,
    dataset: Optional[str],
    collection: Optional[str],
    arg: Optional[List[Tuple[str, str]]] = None,
    target: Optional[str] = None,
    no_ingest: bool = False,
    submit: bool = False,
    upsert: bool = False,
    workflow_id: Optional[str] = None,
) -> None:
    arg = arg or []
    ds_config, collection_config = _configs_from_cli(dataset, arg, collection)

    workflow_def = create_reprocess_chunkset_workflow(
        ds_config,
        collection_config,
        chunk_id,
        asset_uri,
        ingest=not no_ingest,
        ingest_options=None,
        target=target,
        tags=None,
    )

    cli_handle_workflow(
        ctx,
        workflow_def,
        workflow_id=workflow_id,
        upsert=upsert,
        upsert_and_submit=submit,
        args={a[0]: a[1] for a in arg},
    )


def process_items_cmd(
    ctx: click.Context,
    chunkset_id: str,
    dataset: Optional[str],
    collection: Optional[str],
    arg: Optional[List[Tuple[str, str]]] = None,
    target: Optional[str] = None,
    no_ingest: bool = False,
    use_existing_chunks: bool = False,
    since: Optional[str] = None,
    limit: Optional[int] = None,
    submit: bool = False,
    upsert: bool = False,
    workflow_id: Optional[str] = None,
    is_update_workflow: bool = False,
) -> None:
    """Generate the workflow to create and ingest items.

    Read the asset paths from the chunk file at CHUNK and
    submit a workflow to process into items and ingest into
    the database.

    Output: If -s is present, will print the run ID to stdout. Otherwise,
    will print the workflow yaml.
    """
    arg = arg or []
    ds_config, collection_config = _configs_from_cli(dataset, arg, collection)

    workflow_def = create_process_items_workflow(
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
        is_update_workflow=is_update_workflow,
    )

    cli_handle_workflow(
        ctx,
        workflow_def,
        workflow_id=workflow_id,
        upsert=upsert,
        upsert_and_submit=submit,
        args={a[0]: a[1] for a in arg},
    )


def ingest_collection_cmd(
    ctx: click.Context,
    dataset: Optional[str],
    collection: Optional[str],
    arg: List[Tuple[str, str]] = [],
    target: Optional[str] = None,
    submit: bool = False,
    upsert: bool = False,
    workflow_id: Optional[str] = None,
) -> None:
    """Generate the workflow to ingest a collection.

    This will read a collection JSON or template directory,
    specified by the "template" property of the collection
    configuration of the dataset YAML.

    Output: If -s is present, will print the run ID to stdout. Otherwise,
    will print the workflow yaml.
    """
    try:
        ds_config = template_dataset_file(dataset, dict(arg))
    except (MarkedYAMLError, YamlValidationError) as e:
        raise click.ClickException(f"Invalid dataset config.\n{e}")
    except FileNotFoundError:
        raise click.ClickException(
            "No dataset config found. Use --dataset to specify "
            f"or name your config {DEFAULT_DATASET_YAML_PATH}."
        )
    if not ds_config:
        raise click.ClickException("No dataset config found.")

    try:
        collection_config = ds_config.get_collection(collection)
    except MultipleCollectionsError as e:
        raise _handle_multiple_collections(e)

    if not collection_config.template:
        raise click.ClickException(
            f"'template' not specified for collection {collection_config.id}"
        )

    workflow_def = create_ingest_collection_workflow(
        dataset=ds_config,
        collection=collection_config,
        target=target,
        tags=None,
    )

    cli_handle_workflow(
        ctx,
        workflow_def,
        workflow_id=workflow_id,
        upsert=upsert,
        upsert_and_submit=submit,
        args={a[0]: a[1] for a in arg},
    )


def list_collections_cmd(
    ctx: click.Context,
    dataset: Optional[str],
    arg: List[Tuple[str, str]] = [],
) -> None:
    """Lists the collection IDs contained in a dataset configuration."""
    try:
        ds_config = template_dataset_file(dataset, dict(arg))
    except (MarkedYAMLError, YamlValidationError) as e:
        raise click.ClickException(f"Invalid dataset config.\n{e}")
    except FileNotFoundError:
        raise click.ClickException(
            "No dataset config found. Use --dataset to specify "
            f"or name your config {DEFAULT_DATASET_YAML_PATH}."
        )
    if not ds_config:
        raise click.ClickException("No dataset config found.")

    for collection in ds_config.collections:
        cli_output(collection.id)

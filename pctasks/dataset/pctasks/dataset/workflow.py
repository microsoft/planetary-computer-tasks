import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from pctasks.core.models.base import ForeachConfig
from pctasks.core.models.task import TaskDefinition
from pctasks.core.models.workflow import JobDefinition, WorkflowDefinition
from pctasks.core.utils import map_opt
from pctasks.dataset.chunks.models import (
    ChunkInfo,
    CreateChunksTaskConfig,
    ListChunksTaskConfig,
)
from pctasks.dataset.items.models import CreateItemsOptions, CreateItemsTaskConfig
from pctasks.dataset.models import ChunkOptions, CollectionDefinition, DatasetDefinition
from pctasks.dataset.splits.models import CreateSplitsOptions, CreateSplitsTaskConfig
from pctasks.ingest.models import IngestNdjsonInput, IngestTaskConfig
from pctasks.ingest.settings import IngestOptions
from pctasks.ingest.utils import generate_collection_json


def task_tags(
    collection_id: str,
    task_name: str,
    tags: Optional[Dict[str, str]] = None,
    task_config: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, str]]:
    """
    Extracts tags that are defined under a specific collection and task from
    the task_config dictionary defined in a dataset.yaml. The extracted tags are
    merged with any tags directly passed to a workflow creation function. If
    there is a conflict between tags (same key), the task_config tags (those
    defined in a dataset.yaml) will take precedence.

    Args:
        collection_id (str): ID of collection from which to parse task tags.
        task_name (str): ID of task from which to parse tags.
        tags (Optional[Dict[str, str]]): A dictionary of tags that was passed
            directly to one of the create workflow functions, e.g., via the
            `tags` parameter in the `create_chunks_workflow` function.
        task_config (Optional[Dict[str, Any]]): A nested dictionary of task
            configuration objects, keyed by collection, task, and configuration.
            The dictionary is parsed for the `tags` configuration object, which
            is a dictionary of tag key-value pairs. The source of the
            `task_config` object is a dataset.yaml file.

    Returns:
        Optional[Dict[str, str]]: A merged dictionary of tag key-value pairs.
    """
    task_config_ = task_config or {}
    tags_ = tags or {}
    merged_tags = {
        **tags_,
        **task_config_.get(collection_id, {}).get(task_name, {}).get("tags", {}),
    }
    return merged_tags or None


def create_chunks_workflow(
    dataset: DatasetDefinition,
    collection: CollectionDefinition,
    chunkset_id: str,
    create_splits_options: Optional[CreateSplitsOptions] = None,
    chunk_options: Optional[ChunkOptions] = None,
    target: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None,
) -> WorkflowDefinition:

    create_splits_task = CreateSplitsTaskConfig.from_collection(
        dataset,
        collection,
        options=create_splits_options or CreateSplitsOptions(),
        chunk_options=chunk_options,
        environment=dataset.environment,
        tags=task_tags(collection.id, "create-splits", tags, dataset.task_config),
    )

    create_splits_job = JobDefinition(id="create-splits", tasks=[create_splits_task])

    create_chunks_task = CreateChunksTaskConfig.from_collection(
        ds=dataset,
        collection=collection,
        chunkset_id=chunkset_id,
        src_uri="${{ item.uri }}",
        environment=dataset.environment,
        tags=task_tags(collection.id, "create-chunks", tags, dataset.task_config),
        options="${{ item.chunk_options }}",
    )

    create_chunks_job = JobDefinition(
        id="create-chunks",
        tasks=[create_chunks_task],
        foreach=ForeachConfig(
            items="${{ "
            + (
                f"jobs.{create_splits_job.id}."
                f"tasks.{create_splits_task.id}.output.splits"
            )
            + " }}"
        ),
    )

    id = f"{collection.id}-create-chunks"
    if collection.id != dataset.id:
        id = f"{dataset.id}-{id}"
    return WorkflowDefinition(
        id=id,
        name=f"Create chunks for {collection.id}",
        dataset=dataset.id,
        tokens=collection.get_tokens(),
        args=dataset.args,
        jobs={
            create_splits_job.get_id(): create_splits_job,
            create_chunks_job.get_id(): create_chunks_job,
        },
        target=target,
    )


def create_process_items_workflow(
    dataset: DatasetDefinition,
    collection: CollectionDefinition,
    chunkset_id: str,
    use_existing_chunks: bool = False,
    force: bool = False,
    ingest: bool = True,
    create_splits_options: Optional[CreateSplitsOptions] = None,
    chunk_options: Optional[ChunkOptions] = None,
    create_items_options: Optional[CreateItemsOptions] = None,
    ingest_options: Optional[IngestOptions] = None,
    target: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None,
    is_update_workflow: bool = False,
) -> WorkflowDefinition:

    chunks_job_id: str
    chunks_jobs: Dict[str, JobDefinition] = {}
    if use_existing_chunks:
        list_chunks_task = ListChunksTaskConfig.from_collection(
            dataset,
            collection,
            chunkset_id=chunkset_id,
            all=force,
            environment=dataset.environment,
            tags=task_tags(collection.id, "list-chunks", tags, dataset.task_config),
        )
        list_chunks_job = JobDefinition(id="list-chunks", tasks=[list_chunks_task])
        chunks_job_id = list_chunks_job.get_id()
        chunks_jobs = {list_chunks_job.get_id(): list_chunks_job}
    else:
        create_splits_task = CreateSplitsTaskConfig.from_collection(
            dataset,
            collection,
            options=create_splits_options or CreateSplitsOptions(),
            chunk_options=chunk_options,
            environment=dataset.environment,
            tags=task_tags(collection.id, "create-splits", tags, dataset.task_config),
        )

        create_splits_job = JobDefinition(
            id="create-splits", tasks=[create_splits_task]
        )

        create_chunks_task = CreateChunksTaskConfig.from_collection(
            ds=dataset,
            collection=collection,
            chunkset_id=chunkset_id,
            src_uri="${{ item.uri }}",
            environment=dataset.environment,
            tags=task_tags(collection.id, "create-chunks", tags, dataset.task_config),
            options="${{ item.chunk_options }}",
        )

        create_chunks_job = JobDefinition(
            id="create-chunks",
            needs=create_splits_job.id,
            tasks=[create_chunks_task],
            foreach=ForeachConfig(
                items="${{ "
                + (
                    f"jobs.{create_splits_job.id}."
                    f"tasks.{create_splits_task.id}.output.splits"
                )
                + " }}"
            ),
        )

        chunks_job_id = create_chunks_job.get_id()
        chunks_jobs = {
            create_splits_job.get_id(): create_splits_job,
            create_chunks_job.get_id(): create_chunks_job,
        }

    items_tasks: List[TaskDefinition] = []

    create_items_task = CreateItemsTaskConfig.from_collection(
        dataset,
        collection,
        chunkset_id=chunkset_id,
        asset_chunk_info=ChunkInfo(
            uri="${{ item.uri }}", chunk_id="${{ item.chunk_id }}"
        ),
        options=create_items_options,
        environment=dataset.environment,
        tags=task_tags(collection.id, "create-items", tags, dataset.task_config),
    )
    items_tasks.append(create_items_task)

    if ingest:
        ingest_items_task = IngestTaskConfig.create(
            "ingest-items",
            content=IngestNdjsonInput(
                uris=["${{" + f"tasks.{create_items_task.id}.output.ndjson_uri" + "}}"],
            ),
            target=target,
            environment=dataset.environment,
            tags=task_tags(collection.id, "ingest-items", tags, dataset.task_config),
            options=ingest_options,
        )
        items_tasks.append(ingest_items_task)

    process_items_job = JobDefinition(
        id="process-chunk",
        needs=chunks_job_id,
        tasks=items_tasks,
        foreach=ForeachConfig(
            items="${{ "
            + (f"jobs.{chunks_job_id}." f"tasks.{chunks_job_id}.output.chunks")
            + " }}"
        ),
    )

    id = f"{collection.id}-process-items"
    if collection.id != dataset.id:
        id = f"{dataset.id}-{id}"
    workflow_definition = WorkflowDefinition(
        id=id,
        name=f"Process items for {collection.id}",
        dataset=dataset.id,
        tokens=collection.get_tokens(),
        args=dataset.args,
        jobs={
            **chunks_jobs,
            process_items_job.get_id(): process_items_job,
        },
        target_environment=target,
    )

    if is_update_workflow:
        if workflow_definition.args is None:
            workflow_definition = workflow_definition.copy(update={"args": ["since"]})
        else:
            workflow_definition.args.append("since")
        
        for input_ in workflow_definition.jobs["create-splits"].tasks[0].args["inputs"]:
            input_["chunk_options"]["since"] = "${{ args.since }}"

    return workflow_definition


def create_ingest_collection_workflow(
    dataset: DatasetDefinition,
    collection: CollectionDefinition,
    target: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None,
) -> WorkflowDefinition:
    collection_template = map_opt(Path, collection.template)
    if not collection_template:
        raise ValueError(f"Collection {collection.id} has no template")

    if collection_template.is_dir():
        collection_body = generate_collection_json(collection_template)
    else:
        with open(collection_template, "r") as f:
            collection_body = json.load(f)

    # Ensure collection ID is set properly
    existing_collection_id = collection_body.get("id")
    if existing_collection_id and existing_collection_id != collection.id:
        raise ValueError(
            f"Collection has ID {existing_collection_id}, expected {collection.id}"
        )
    else:
        collection_body["id"] = collection.id

    task = IngestTaskConfig.from_collection(
        collection=collection_body,
        target=target,
        environment=dataset.environment,
        tags=task_tags(collection.id, "ingest-collection", tags, dataset.task_config),
    )

    id = f"{collection.id}-ingest-collection"
    if collection.id != dataset.id:
        id = f"{dataset.id}-{id}"
    return WorkflowDefinition(
        id=id,
        name=f"Ingest Collection: {collection.id}",
        dataset_id=f"{dataset.id}/{collection.id}",
        target_environment=target,
        args=dataset.args,
        jobs={
            "ingest-collection": JobDefinition(tasks=[task]),
        },
    )

from typing import Dict, List, Optional

from pctasks.core.models.base import ForeachConfig
from pctasks.core.models.task import TaskConfig
from pctasks.core.models.workflow import JobConfig, WorkflowConfig
from pctasks.dataset.chunks.models import (
    ChunkInfo,
    CreateChunksTaskConfig,
    ListChunksTaskConfig,
)
from pctasks.dataset.items.models import CreateItemsOptions, CreateItemsTaskConfig
from pctasks.dataset.models import ChunkOptions, CollectionConfig, DatasetConfig
from pctasks.dataset.splits.models import CreateSplitsOptions, CreateSplitsTaskConfig
from pctasks.ingest.models import IngestNdjsonInput, IngestTaskConfig
from pctasks.ingest.settings import IngestOptions


def create_chunks_workflow(
    dataset: DatasetConfig,
    collection: CollectionConfig,
    chunkset_id: str,
    create_splits_options: Optional[CreateSplitsOptions] = None,
    chunk_options: Optional[ChunkOptions] = None,
    target: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None,
) -> WorkflowConfig:

    create_splits_task = CreateSplitsTaskConfig.from_collection(
        dataset,
        collection,
        options=create_splits_options or CreateSplitsOptions(),
        chunk_options=chunk_options,
        environment=dataset.environment,
        tags=tags,
    )

    create_splits_job = JobConfig(id="create-splits", tasks=[create_splits_task])

    create_chunks_task = CreateChunksTaskConfig.from_collection(
        ds=dataset,
        collection=collection,
        chunkset_id=chunkset_id,
        src_uri="${{ item.uri }}",
        environment=dataset.environment,
        tags=tags,
        options="${{ item.chunk_options }}",
    )

    create_chunks_job = JobConfig(
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

    return WorkflowConfig(
        name=f"Create chunks for {collection.id}",
        dataset=dataset.get_identifier(),
        tokens=collection.get_tokens(),
        args=dataset.args,
        jobs={
            create_splits_job.get_id(): create_splits_job,
            create_chunks_job.get_id(): create_chunks_job,
        },
        target=target,
    )


def create_process_items_workflow(
    dataset: DatasetConfig,
    collection: CollectionConfig,
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
) -> WorkflowConfig:

    chunks_job_id: str
    chunks_jobs: Dict[str, JobConfig] = {}
    if use_existing_chunks:
        list_chunks_task = ListChunksTaskConfig.from_collection(
            dataset,
            collection,
            chunkset_id=chunkset_id,
            all=force,
            environment=dataset.environment,
            tags=tags,
        )
        list_chunks_job = JobConfig(id="list-chunks", tasks=[list_chunks_task])
        chunks_job_id = list_chunks_job.get_id()
        chunks_jobs = {list_chunks_job.get_id(): list_chunks_job}
    else:
        create_splits_task = CreateSplitsTaskConfig.from_collection(
            dataset,
            collection,
            options=create_splits_options or CreateSplitsOptions(),
            chunk_options=chunk_options,
            environment=dataset.environment,
            tags=tags,
        )

        create_splits_job = JobConfig(id="create-splits", tasks=[create_splits_task])

        create_chunks_task = CreateChunksTaskConfig.from_collection(
            ds=dataset,
            collection=collection,
            chunkset_id=chunkset_id,
            src_uri="${{ item.uri }}",
            environment=dataset.environment,
            tags=tags,
            options="${{ item.chunk_options }}",
        )

        create_chunks_job = JobConfig(
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

    items_tasks: List[TaskConfig] = []

    create_items_task = CreateItemsTaskConfig.from_collection(
        dataset,
        collection,
        chunkset_id=chunkset_id,
        asset_chunk_info=ChunkInfo(
            uri="${{ item.uri }}", chunk_id="${{ item.chunk_id }}"
        ),
        options=create_items_options,
        environment=dataset.environment,
        tags=tags,
    )
    items_tasks.append(create_items_task)

    if ingest:
        ingest_items_task = IngestTaskConfig.create(
            "ingest-items",
            content=IngestNdjsonInput(
                uris=[
                    "${{ " + f"tasks.{create_items_task.id}.output.ndjson_uri" + "}} "
                ],
            ),
            target=target,
            environment=dataset.environment,
            tags=tags,
            options=ingest_options,
        )
        items_tasks.append(ingest_items_task)

    process_items_job = JobConfig(
        id="process-chunk",
        needs=chunks_job_id,
        tasks=items_tasks,
        foreach=ForeachConfig(
            items="${{ "
            + (f"jobs.{chunks_job_id}." f"tasks.{chunks_job_id}.output.chunks")
            + " }}"
        ),
    )

    return WorkflowConfig(
        name=f"Process items for {collection.id}",
        dataset=dataset.get_identifier(),
        tokens=collection.get_tokens(),
        args=dataset.args,
        jobs={
            **chunks_jobs,
            process_items_job.get_id(): process_items_job,
        },
        target_environment=target,
    )

from typing import Dict, List, Optional
from pctasks.core.models.base import ForeachConfig
from pctasks.core.models.task import TaskConfig

from pctasks.core.models.workflow import JobConfig, WorkflowConfig
from pctasks.dataset.chunks.models import CreateChunksTaskConfig

from pctasks.dataset.items.models import CreateItemsOptions, CreateItemsTaskConfig
from pctasks.dataset.models import CollectionConfig, DatasetConfig
from pctasks.dataset.splits.models import CreateSplitsOptions, CreateSplitsTaskConfig
from pctasks.ingest.models import IngestNdjsonInput, IngestTaskConfig
from pctasks.ingest.settings import IngestOptions


class ProcessItemsWorkflowConfig(WorkflowConfig):
    @classmethod
    def from_collection(
        cls,
        dataset: DatasetConfig,
        collection: CollectionConfig,
        chunkset_id: str,
        ingest: bool = False,
        create_splits_options: Optional[CreateSplitsOptions] = None,
        create_items_options: Optional[CreateItemsOptions] = None,
        ingest_options: Optional[IngestOptions] = None,
        target: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> "ProcessItemsWorkflowConfig":

        create_splits_task = CreateSplitsTaskConfig.from_collection(
            dataset,
            collection,
            options=create_splits_options or CreateSplitsOptions(),
            environment=dataset.environment,
            tags=tags,
        )

        create_splits_job = JobConfig(id="create-splits", tasks=[create_splits_task])

        create_chunks_task = CreateChunksTaskConfig.from_collection(
            ds=dataset,
            collection=collection,
            chunkset_id=chunkset_id,
            src_storage_uri="${{ item.uri }}",
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

        items_tasks: List[TaskConfig] = []

        create_items_task = CreateItemsTaskConfig.from_collection(
            dataset,
            collection,
            chunkset_id=chunkset_id,
            asset_chunk_uri="${{ item.uri }}",
            chunk_id="${{ item.chunk_id }}",
            options=create_items_options,
            environment=dataset.environment,
            tags=tags,
        )
        items_tasks.append(create_items_task)

        if ingest:
            ingest_items_task = IngestTaskConfig.create(
                "ingest-items",
                content=IngestNdjsonInput(
                    uris=[f"tasks.{create_items_task.id}." "output.ndjson_uri"],
                ),
                target=target,
                environment=dataset.environment,
                tags=tags,
                options=ingest_options,
            )
            items_tasks.append(ingest_items_task)

        process_items_job = JobConfig(
            id="process-chunk",
            tasks=items_tasks,
            foreach=ForeachConfig(
                items="${{ "
                + (
                    f"jobs.{create_chunks_job.id}."
                    f"tasks.{create_chunks_task.id}.output.chunks"
                )
                + " }}"
            ),
        )

        return ProcessItemsWorkflowConfig(
            name=f"Process items for {collection.id}",
            dataset=dataset.get_identifier(),
            tokens=collection.get_tokens(),
            args=dataset.args,
            jobs={
                create_splits_job.get_id(): create_splits_job,
                create_chunks_job.get_id(): create_chunks_job,
                process_items_job.get_id(): process_items_job,
            },
        )

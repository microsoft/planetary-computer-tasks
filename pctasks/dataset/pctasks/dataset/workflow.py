from typing import Dict, Optional

from pctasks.core.models.workflow import JobConfig, WorkflowConfig
from pctasks.dataset.chunks.models import CreateChunksOptions, CreateChunksTaskConfig
from pctasks.dataset.items.models import CreateItemsOptions, CreateItemsTaskConfig
from pctasks.dataset.models import CollectionConfig, DatasetConfig
from pctasks.dataset.splits.models import CreateSplitsTaskConfig
from pctasks.execute.constants import JOBS_TEMPLATE_PATH
from pctasks.ingest.models import IngestNdjsonInput, IngestTaskConfig
from pctasks.ingest.settings import IngestOptions
from pctasks.ingest_task.constants import DB_CONNECTION_STRING_ENV_VALUE


class ProcessItemsWorkflowConfig(WorkflowConfig):
    @classmethod
    def from_collection(
        cls,
        dataset: DatasetConfig,
        collection: CollectionConfig,
        chunkset_id: str,
        db_connection_str: str,
        create_chunks_options: Optional[CreateChunksOptions] = None,
        create_items_options: Optional[CreateItemsOptions] = None,
        ingest_options: Optional[IngestOptions] = None,
        target: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> "ProcessItemsWorkflowConfig":
        create_splits_task = CreateSplitsTaskConfig.from_collection(dataset, collection)

        create_splits_job = JobConfig(id="create-splits", tasks=[create_splits_task])

        create_chunks_task = CreateChunksTaskConfig.from_collection(
            dataset,
            collection,
            src_uri=(
                f"{JOBS_TEMPLATE_PATH}.{create_splits_job.get_id()}."
                f"tasks.{create_splits_task.id}."
                "output.uris"
            ),
            chunkset_id=chunkset_id,
            options=create_chunks_options,
        )

        create_chunks_job = JobConfig(id="create-chunks", tasks=[create_chunks_task])

        create_items_task = CreateItemsTaskConfig.from_collection(
            dataset,
            collection,
            options=create_items_options,
        )

        ingest_items_task = IngestTaskConfig.create(
            "ingest-items",
            content=IngestNdjsonInput(
                uris=[f"tasks.{create_items_task.id}." "output.ndjson_uri"],
            ),
            target=target,
            tags=tags,
            ingest_options=ingest_options,
            environment={DB_CONNECTION_STRING_ENV_VALUE: db_connection_str},
        )

        process_chunk_job = JobConfig(
            id="process-chunk", tasks=[create_items_task, ingest_items_task]
        )

        return ProcessItemsWorkflowConfig(
            name=f"Process items for {collection.id}",
            dataset=dataset.get_identifier(),
            tokens=collection.get_tokens(),
            args=dataset.args,
            jobs={
                create_splits_job.get_id(): create_splits_job,
                create_chunks_job.get_id(): create_chunks_job,
                process_chunk_job.get_id(): process_chunk_job,
            },
        )

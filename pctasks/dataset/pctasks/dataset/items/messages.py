from typing import Dict, Optional

from pctasks.core.models.tokens import StorageAccountTokens
from pctasks.core.models.workflow import (
    JobConfig,
    TaskConfig,
    WorkflowConfig,
    WorkflowSubmitMessage,
)
from pctasks.dataset.constants import CREATE_ITEMS_TASK_ID
from pctasks.dataset.items.models import CreateItemsInput
from pctasks.ingest.models import IngestNdjsonInput, IngestTaskConfig
from pctasks.ingest.settings import IngestConfig


class ProcessItemsWorkflow(WorkflowSubmitMessage):
    @classmethod
    def create(
        cls,
        collection_id: str,
        image: str,
        collection_class: str,
        asset_chunk_uri: str,
        item_chunk_uri: str,
        tokens: Optional[Dict[str, StorageAccountTokens]] = None,
        storage_account_url: Optional[str] = None,
        limit: Optional[int] = None,
        skip_validation: bool = False,
        environment: Optional[Dict[str, str]] = None,
        tags: Optional[Dict[str, str]] = None,
        target: Optional[str] = None,
        ingest_config: Optional[IngestConfig] = None,
    ) -> "ProcessItemsWorkflow":
        create_items_task: TaskConfig = TaskConfig(
            id=CREATE_ITEMS_TASK_ID,
            image=image,
            task=f"{collection_class}.create_items",
            args=CreateItemsInput(
                chunk_uri=asset_chunk_uri,
                output_uri=item_chunk_uri,
                tokens=tokens,
                storage_endpoint_url=storage_account_url,
                limit=limit,
                skip_validation=skip_validation,
            ).dict(),
            environment=environment,
            tags=tags,
        )

        ingest_items_task: TaskConfig = IngestTaskConfig.create(
            "ingest-items",
            content=IngestNdjsonInput(collection=collection_id, uris=[item_chunk_uri]),
            target=target,
            tags=tags,
            environment=environment,
            ingest_config=ingest_config,
        )

        return ProcessItemsWorkflow(
            workflow=WorkflowConfig(
                name=f"Process Items for {collection_id}",
                tokens=None,
                on=None,
                jobs={
                    "process-items": JobConfig(
                        id=f"Process Items for {collection_id}",
                        tasks=[create_items_task, ingest_items_task],
                    )
                },
            )
        )

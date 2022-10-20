from typing import Dict, List, Optional

from pctasks.core.models.base import PCBaseModel
from pctasks.core.models.config import CodeConfig
from pctasks.core.models.task import TaskDefinition
from pctasks.dataset.models import (
    ChunkOptions,
    CollectionDefinition,
    DatasetDefinition,
    SplitDefinition,
)
from pctasks.dataset.splits.constants import (
    CREATE_SPLITS_TASK_ID,
    CREATE_SPLITS_TASK_PATH,
)


class CreateSplitsOptions(PCBaseModel):
    limit: Optional[int] = None


class SplitInput(PCBaseModel):
    """Configuration for a split task for a single URI."""

    uri: str
    splits: Optional[List[SplitDefinition]] = None
    sas_token: Optional[str] = None
    chunk_options: ChunkOptions
    """Chunk options for the split."""


class CreateSplitsInput(PCBaseModel):
    """Input for a split task."""

    inputs: List[SplitInput]
    options: CreateSplitsOptions = CreateSplitsOptions()


class SplitTarget(PCBaseModel):
    """Target for a split task."""

    uri: str
    """URI of the split."""

    chunk_options: ChunkOptions
    """Chunk options for the split."""


class CreateSplitsOutput(PCBaseModel):
    splits: List[SplitTarget]


class CreateSplitsTaskConfig(TaskDefinition):
    @classmethod
    def create(
        cls,
        image: str,
        args: CreateSplitsInput,
        task: str = CREATE_SPLITS_TASK_PATH,
        code: Optional[CodeConfig] = None,
        environment: Optional[Dict[str, str]] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> "CreateSplitsTaskConfig":
        return CreateSplitsTaskConfig(
            id=CREATE_SPLITS_TASK_ID,
            image=image,
            code=code,
            args=args.dict(),
            task=task,
            environment=environment,
            tags=tags,
        )

    @classmethod
    def from_collection(
        cls,
        ds: DatasetDefinition,
        collection: CollectionDefinition,
        options: Optional[CreateSplitsOptions] = None,
        chunk_options: Optional[ChunkOptions] = None,
        environment: Optional[Dict[str, str]] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> "CreateSplitsTaskConfig":
        split_inputs: List[SplitInput] = []
        for asset_storage_config in collection.asset_storage:
            sas_token = asset_storage_config.token

            storage_chunk_options = asset_storage_config.chunks.options
            if chunk_options:
                storage_chunk_options = storage_chunk_options.copy(
                    update=chunk_options.dict(exclude_defaults=True)
                )
            split_inputs.append(
                SplitInput(
                    uri=asset_storage_config.uri,
                    splits=asset_storage_config.chunks.splits,
                    sas_token=sas_token,
                    chunk_options=storage_chunk_options,
                )
            )

        return cls.create(
            image=ds.image,
            code=ds.code,
            args=CreateSplitsInput(
                inputs=split_inputs, options=options or CreateSplitsOptions()
            ),
            task=f"{collection.collection_class}.create_splits_task",
            environment=environment,
            tags=tags,
        )

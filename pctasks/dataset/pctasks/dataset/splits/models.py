from typing import Dict, List, Optional

from pctasks.core.models.base import PCBaseModel
from pctasks.core.models.task import TaskConfig
from pctasks.dataset.models import (
    BlobStorageConfig,
    ChunkOptions,
    CollectionConfig,
    DatasetConfig,
    SplitConfig,
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
    splits: Optional[List[SplitConfig]] = None
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


class CreateSplitsTaskConfig(TaskConfig):
    @classmethod
    def create(
        cls,
        image: str,
        args: CreateSplitsInput,
        environment: Optional[Dict[str, str]] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> "CreateSplitsTaskConfig":
        return CreateSplitsTaskConfig(
            id=CREATE_SPLITS_TASK_ID,
            image=image,
            args=args.dict(),
            task=CREATE_SPLITS_TASK_PATH,
            environment=environment,
            tags=tags,
        )

    @classmethod
    def from_collection(
        cls,
        ds: DatasetConfig,
        collection: CollectionConfig,
        options: Optional[CreateSplitsOptions] = None,
        environment: Optional[Dict[str, str]] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> "CreateSplitsTaskConfig":
        split_inputs: List[SplitInput] = []
        for asset_storage_config in collection.asset_storage:
            sas_token: Optional[str] = None
            if isinstance(asset_storage_config, BlobStorageConfig):
                sas_token = asset_storage_config.sas_token
            split_inputs.append(
                SplitInput(
                    uri=asset_storage_config.get_uri(),
                    splits=asset_storage_config.chunks.splits,
                    sas_token=sas_token,
                    chunk_options=asset_storage_config.chunks.options,
                )
            )

        return cls.create(
            image=ds.image,
            args=CreateSplitsInput(
                inputs=split_inputs, options=options or CreateSplitsOptions()
            ),
            environment=environment,
            tags=tags,
        )

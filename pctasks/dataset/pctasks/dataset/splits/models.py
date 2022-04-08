from typing import Dict, List, Optional

from pctasks.core.models.base import PCBaseModel
from pctasks.core.models.task import TaskConfig
from pctasks.dataset.models import (
    BlobStorageConfig,
    CollectionConfig,
    DatasetConfig,
    SplitConfig,
)
from pctasks.dataset.splits.constants import (
    CREATE_SPLITS_TASK_ID,
    CREATE_SPLITS_TASK_PATH,
)


class SplitInput(PCBaseModel):
    """Configuration for a split task for a single URI."""

    uri: str
    splits: Optional[List[SplitConfig]] = None
    sas_token: Optional[str] = None


class CreateSplitsInput(PCBaseModel):
    """Input for a split task."""

    inputs: List[SplitInput]
    limit: Optional[int] = None


class CreateSplitsOutput(PCBaseModel):
    uris: List[str]


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
        limit: Optional[int] = None,
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
                )
            )

        return cls.create(
            image=ds.image,
            args=CreateSplitsInput(inputs=split_inputs, limit=limit),
            environment=environment,
            tags=tags,
        )

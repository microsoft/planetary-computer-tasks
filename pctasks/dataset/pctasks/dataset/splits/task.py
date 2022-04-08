import logging
from typing import List, Union

from pctasks.core.models.task import FailedTaskResult, WaitTaskResult
from pctasks.dataset.splits.models import CreateSplitsInput, CreateSplitsOutput
from pctasks.task import Task
from pctasks.task.context import TaskContext

logger = logging.getLogger(__name__)


class CreateSplitsTask(Task[CreateSplitsInput, CreateSplitsOutput]):
    _input_model = CreateSplitsInput
    _output_model = CreateSplitsOutput

    def run(
        self, input: CreateSplitsInput, context: TaskContext
    ) -> Union[CreateSplitsOutput, WaitTaskResult, FailedTaskResult]:
        uris: List[str] = []
        for splits_input in input.inputs:
            assets_uri = splits_input.uri
            storage = context.storage_factory.get_storage(assets_uri)
            logger.debug(f"Processing {assets_uri}...")
            if splits_input.splits:
                splits = splits_input.splits
                logger.debug(f"{len(splits)} splits found.")

                logger.info(f"Walking prefixes in {assets_uri}...")
                split_prefixes = [
                    s.prefix + "/"
                    if s.prefix and not s.prefix.endswith("/")
                    else s.prefix
                    for s in splits
                ]
                for split_config in splits:
                    split_prefix = split_config.prefix
                    split_prefixes = split_prefixes[1:]

                    for root, folders, _ in storage.walk(
                        max_depth=split_config.depth,
                        min_depth=split_config.depth,
                        name_starts_with=split_prefix,
                        walk_limit=input.limit,
                        file_limit=input.limit,
                    ):
                        print(".", end="", flush=True)
                        # Avoid walking through the same prefix twice
                        if split_prefixes:
                            for other_prefix in split_prefixes:
                                if other_prefix in folders:
                                    folders.remove(other_prefix)

                        uris.append(storage.get_uri(root))

                print()

            else:
                uris.append(assets_uri)

        return CreateSplitsOutput(uris=uris)


create_splits_task = CreateSplitsTask()

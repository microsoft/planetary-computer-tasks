import logging
from typing import List, Union

from pctasks.core.models.task import FailedTaskResult, WaitTaskResult
from pctasks.dataset.splits.models import (
    CreateSplitsInput,
    CreateSplitsOutput,
    SplitTarget,
)
from pctasks.task import Task
from pctasks.task.context import TaskContext

logger = logging.getLogger(__name__)


class CreateSplitsTask(Task[CreateSplitsInput, CreateSplitsOutput]):
    _input_model = CreateSplitsInput
    _output_model = CreateSplitsOutput

    def run(
        self, input: CreateSplitsInput, context: TaskContext
    ) -> Union[CreateSplitsOutput, WaitTaskResult, FailedTaskResult]:
        split_targets: List[SplitTarget] = []
        split_limit_hit = False
        for splits_input in input.inputs:
            if split_limit_hit:
                break

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
                    ):
                        print(".", end="", flush=True)
                        # Avoid walking through the same prefix twice
                        if split_prefixes:
                            for other_prefix in split_prefixes:
                                if other_prefix in folders:
                                    folders.remove(other_prefix)

                        split_targets.append(
                            SplitTarget(
                                uri=storage.get_uri(root),
                                chunk_options=splits_input.chunk_options,
                            )
                        )

                        if (
                            input.options.limit
                            and len(split_targets) >= input.options.limit
                        ):
                            split_limit_hit = True
                            break

                print()

            else:
                split_targets.append(
                    SplitTarget(
                        uri=assets_uri, chunk_options=splits_input.chunk_options
                    )
                )

        return CreateSplitsOutput(splits=split_targets)


create_splits_task = CreateSplitsTask()

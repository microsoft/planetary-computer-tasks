import json
import logging
from typing import Callable, List, Union

import pystac

from pctasks.core.models.task import FailedTaskResult, WaitTaskResult
from pctasks.core.storage import StorageFactory
from pctasks.core.tokens import Tokens
from pctasks.dataset.items.models import CreateItemsInput, CreateItemsOutput
from pctasks.task import Task
from pctasks.task.context import TaskContext

logger = logging.getLogger(__name__)


CreateItemFunc = Callable[
    [str, StorageFactory], Union[List[pystac.Item], WaitTaskResult]
]


class OutputNDJSONRequired(Exception):
    pass


class CreateItemsTask(Task[CreateItemsInput, CreateItemsOutput]):
    _input_model = CreateItemsInput
    _output_model = CreateItemsOutput

    def __init__(
        self,
        create_item: CreateItemFunc,
    ) -> None:
        super().__init__()
        self._create_item = create_item

    def create_items(
        self, args: CreateItemsInput
    ) -> Union[List[pystac.Item], WaitTaskResult]:
        storage_factory = StorageFactory(
            tokens=Tokens(args.tokens), account_url=args.storage_endpoint_url
        )
        results: List[pystac.Item] = []
        if args.asset_uri:
            result = self._create_item(args.asset_uri, storage_factory)
            if isinstance(result, WaitTaskResult):
                return result
            else:
                results.extend(result)
        elif args.chunk_uri:
            chunk_storage, chunk_path = storage_factory.get_storage_for_file(
                args.chunk_uri
            )
            for asset_uri in chunk_storage.read_text(chunk_path).splitlines():
                result = self._create_item(asset_uri, storage_factory)
                if isinstance(result, WaitTaskResult):
                    return result
                else:
                    results.extend(result)
        else:
            # Should be prevented by validator
            raise ValueError("Neither asset_uri nor chunk_uri specified")

        return results

    def run(
        self, input: CreateItemsInput, context: TaskContext
    ) -> Union[CreateItemsOutput, WaitTaskResult, FailedTaskResult]:
        results = self.create_items(input)
        if isinstance(results, WaitTaskResult):
            return results
        elif isinstance(results, FailedTaskResult):
            return results
        else:
            output: CreateItemsOutput
            if len(results) == 1:
                output = CreateItemsOutput(item=results[0].to_dict())
            else:
                # Save ndjson
                if not input.output_uri:
                    raise OutputNDJSONRequired("output_uri must be specified")

                storage, path = context.storage_factory.get_storage_for_file(
                    input.output_uri
                )

                storage.write_text(
                    path, "\n".join([json.dumps(item.to_dict()) for item in results])
                )

                output = CreateItemsOutput(ndjson_uri=input.output_uri)

            return output

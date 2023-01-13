import logging
from pathlib import Path
from typing import Dict

import orjson
from pystac import Item

from pctasks.core.models.base import PCBaseModel
from pctasks.task.context import TaskContext
from pctasks.task.task import Task

handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("[%(levelname)s]:%(asctime)s: %(message)s"))
handler.setLevel(logging.INFO)
logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


class FixItemsInput(PCBaseModel):
    incorrect_chunkset_uri: str
    corrected_chunkset_uri: str


class FixItemsOutput(PCBaseModel):
    corrected_chunkset_uri: str


class FixItems(Task[FixItemsInput, FixItemsOutput]):
    _input_model = FixItemsInput
    _output_model = FixItemsOutput

    def run(self, input: FixItemsInput, context: TaskContext) -> FixItemsOutput:
        storage = context.storage_factory.get_storage(input.incorrect_chunkset_uri)
        paths = storage.list_files(extensions=[".ndjson"])

        for path in paths:
            items_as_dicts = storage.read_ndjson(path)
            fixed_items = list()
            error_items = list()
            for item_dict in items_as_dicts:
                try:
                    fixed_item = remove_classes(item_dict)
                except Exception as e:
                    logger.error(e)
                    error_items.append(item_dict)
                else:
                    fixed_items.append(fixed_item)

            logger.info(
                f"{len(fixed_items)} items fixed, {len(error_items)} errors"
                f"for items in {storage.get_url(path)}"
            )
            fixed_storage, fixed_path = context.storage_factory.get_storage_for_file(
                f"{input.corrected_chunkset_uri}/{path}"
            )
            fixed_storage.write_text(
                fixed_path, "\n".join(orjson.dumps(item).decode("utf-8") for item in fixed_items)
            )

            if error_items:
                error_storage, error_path = context.storage_factory.get_storage_for_file(
                    f"{input.corrected_chunkset_uri}/{Path(path).with_suffix('')}-errors.ndjson"
                )
                error_storage.write_text(
                    error_path,
                    "\n".join(orjson.dumps(item).decode("utf-8") for item in error_items),
                )

        return FixItemsOutput(corrected_chunkset_uri=storage.get_uri(input.corrected_chunkset_uri))


fix_items_task = FixItems()


def remove_classes(item_dict: Dict) -> Item:
    trimmed_classes = item_dict["assets"]["lcpri"]["classification:classes"][0:9]
    item_dict["assets"]["lcpri"]["classification:classes"] = trimmed_classes
    item_dict["assets"]["lcsec"]["classification:classes"] = trimmed_classes
    return item_dict

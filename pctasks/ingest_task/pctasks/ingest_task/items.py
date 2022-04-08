import logging
import os
import time
from concurrent import futures
from dataclasses import dataclass
from tempfile import TemporaryDirectory
from typing import Any, Dict, Iterator, List, Optional

import orjson

# from pypgstac.pypgstac import loadopt
from pypgstac.load import Methods

from pctasks.core.storage import StorageFactory
from pctasks.core.storage.local import LocalStorage
from pctasks.ingest.models import IngestConfig
from pctasks.ingest_task.pgstac import PgSTAC

logger = logging.getLogger(__name__)


class IngestFailedException(Exception):
    pass


def ingest_item(pgstac: PgSTAC, item: Dict[str, Any]) -> None:
    pgstac.ingest_items([orjson.dumps(item)])


@dataclass
class PreparedNdjson:
    uri: str
    prepared_path: str
    line_count: int


def ingest_item_paths(
    prepared_paths: Iterator[str],
    db: PgSTAC,
    insert_group_size: int,
    upsert: bool = True,
) -> None:
    logger.info("=== Ingesting into the database...")
    # if upsert:
    #     mode = loadopt("upsert")
    # else:
    #     mode = loadopt("insert")

    if upsert:
        mode = Methods.upsert
    else:
        mode = Methods.insert

    tic_ingest = time.perf_counter()

    # Concatenate chunkfiles for performance
    with TemporaryDirectory() as tmp_dir:
        target_path = os.path.join(tmp_dir, "items.ndjson")
        path_count = 0
        with open(target_path, "w") as target:
            for path in prepared_paths:
                with open(path) as source:
                    if path_count > 0:
                        target.write("\n")
                    target.write(source.read().strip("\n"))
                    path_count += 1
        try:
            with open(target_path, "rb") as f:
                db.ingest_items(f, mode=mode, insert_group_size=insert_group_size)
            toc_ingest = time.perf_counter()
            logger.info(
                f"--- Ingested items from {path_count} chunksfiles."
                f"in {toc_ingest - tic_ingest:0.4f} seconds"
            )
        except Exception as e:
            logger.exception(e)
            toc_ingest = time.perf_counter()
            logger.info(f"!!! Ingest errored at {toc_ingest - tic_ingest:0.4f} seconds")
            raise


def prepare_chunk(
    ndjson_uri: str,
    local_prepared_dir: str,
    storage_factory: StorageFactory,
) -> PreparedNdjson:
    """Downloads a ndjson file locally. Returns (remote_path, local_path)"""
    storage, path = storage_factory.get_storage_for_file(ndjson_uri)

    local_prepared_storage = LocalStorage(local_prepared_dir)

    local_prepared_storage.ensure_dirs(path)
    local_prepared_path = local_prepared_storage.get_uri(path)

    chunk_text = storage.read_text(path)
    line_count = 0
    with open(local_prepared_path, "w") as f_write:
        for line in chunk_text.split("\n"):
            line_count += 1
            f_write.writelines(line + "\n")

    logger.info(f"Downloaded {ndjson_uri} ({line_count} lines)...")
    return PreparedNdjson(
        uri=ndjson_uri,
        prepared_path=local_prepared_path,
        line_count=line_count,
    )


def ingest_ndjsons(
    pgstac: PgSTAC,
    ndjsons: List[str],
    storage_factory: StorageFactory,
    ingest_config: Optional[IngestConfig] = None,
) -> None:
    ingest_config = ingest_config or IngestConfig()

    # Pool that executes the chunk download and preperation steps
    pool = futures.ProcessPoolExecutor()

    # The list we'll collect from the processes that are tasked with
    # downloading and preparing (parsing into a CSV line) each chunk.
    # Optional because we might not get there, Future as it's
    # work being executed in another process, and a Union type
    # because prepare_chunk will either return a result, or on error
    # return an error record.
    prepared_ndjsons: Optional[List[futures.Future[PreparedNdjson]]] = None

    try:
        logger.info("===== Ingesting ndjsons =====")
        target_insert_group_size = ingest_config.insert_group_size
        upsert = not ingest_config.insert_only

        logger.info(f"--- Starting to process {len(ndjsons)} chunks.")

        total_ndjsons = len(ndjsons)
        success_ndjsons: List[str] = []
        failed_ndjsons: List[str] = []

        try:
            with TemporaryDirectory() as tmp_dir:
                local_prepared_dir = os.path.join(tmp_dir, "prepared")

                logger.info(" -- Preparing chunkset...")

                # Clear the storage factory cache to avoid pickle errors.
                storage_factory.clear_cache()

                prepared_ndjsons = [
                    pool.submit(
                        prepare_chunk,
                        ndjson_uri,
                        local_prepared_dir=local_prepared_dir,
                        storage_factory=storage_factory,
                    )
                    for ndjson_uri in ndjsons
                ]

                insert_group: List[PreparedNdjson] = []
                insert_group_line_count: int = 0

                def flush() -> List[str]:
                    insert_group_paths: List[str] = []
                    insert_group_ids: List[str] = []
                    insert_group_cleanup_files: List[str] = []
                    for ndjson in insert_group:
                        insert_group_ids.append(ndjson.uri)
                        insert_group_paths.append(ndjson.prepared_path)
                        insert_group_cleanup_files.append(ndjson.prepared_path)

                    # flush
                    try:
                        ingest_item_paths(
                            iter(insert_group_paths),
                            pgstac,
                            target_insert_group_size,
                            upsert=upsert,
                        )

                        success_ndjsons.extend(insert_group_ids)

                        logger.info(" -- INSERT GROUP SUCCESS --")
                    except Exception:
                        failed_ndjsons.extend(insert_group_ids)
                        logger.info(" -- INSERT GROUP FAILED --")

                    num_ok = len(success_ndjsons)
                    num_bad = len(failed_ndjsons)
                    logger.info(f"Success: ({(num_ok/total_ndjsons)*100:06.2f}%)")
                    logger.info(f"Failure: ({(num_bad/total_ndjsons)*100:06.2f}%)")
                    logger.info(
                        f"Total:   ({((num_ok+num_bad)/total_ndjsons)*100:06.2f}%)"
                    )
                    logger.info(
                        f"{num_ok + num_bad} out of " f"{total_ndjsons} chunks. "
                    )

                    return insert_group_cleanup_files

                for local_path_future in futures.as_completed(prepared_ndjsons):
                    if not local_path_future.cancelled():
                        prepared_chunk = local_path_future.result()

                        insert_group.append(prepared_chunk)
                        insert_group_line_count += prepared_chunk.line_count

                        logger.info(
                            f"Queued {prepared_chunk.uri} "
                            f"({insert_group_line_count} lines queued)"
                        )

                        if insert_group_line_count >= target_insert_group_size:
                            cleanup_files = flush()
                            insert_group = []
                            insert_group_line_count = 0
                            for local_path in cleanup_files:
                                os.unlink(local_path)

                if len(insert_group) > 0:
                    flush()

        except Exception as e:
            logger.error(e)
            raise
        finally:
            logger.info(" -- Finished Ingest.")

            logger.info("Checking for hanging processes...")
            if prepared_ndjsons is not None:
                for f in prepared_ndjsons:
                    if not f.done():
                        logger.warning("Canceling dangling prepare tasks...")
                        f.cancel()

            logger.info("Shutting down pool...")
            pool.shutdown(wait=True)
            logger.info("...pool shut down.")

            if any(failed_ndjsons):
                raise IngestFailedException(
                    f" Found {len(failed_ndjsons)} failed chunks!"
                )

    except Exception as e:
        logger.exception(e)
        raise

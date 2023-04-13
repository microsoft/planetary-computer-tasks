import contextlib
import logging
import json
import typing
import random
import functools

import azure.storage.blob
import dask
import dask.bag
import dask_kubernetes.operator


import pctasks.core.utils.summary


logger = logging.getLogger(__name__)


@dask.delayed
def list_prefixes(prefix: str, depth: int, storage_options: dict[str, typing.Any]):
    prefix = prefix.rstrip("/") + "/"
    d = prefix.count("/")
    cc = azure.storage.blob.ContainerClient(**storage_options)
    blob_names = []
    with cc:
        if d < depth:
            prefixes = [x.name for x in cc.walk_blobs(prefix)]
            xs = [
                list_prefixes(x, depth, storage_options) for x in prefixes
            ]
            for x in xs:
                blob_names.extend(x.compute())
        elif d == depth:
            return [prefix]
    return blob_names


@dask.delayed
def read_prefix(x: str, storage_options: dict[str, typing.Any], fraction=1.0) -> typing.List[bytes]:
    cc = azure.storage.blob.ContainerClient(**storage_options)
    assert 0 <= fraction <= 1.0

    items: typing.List[bytes] = []
    blobs = list(cc.list_blobs(x))
    blobs = random.sample(blobs, int(len(blobs) * fraction))
    
    with cc:
        for blob in blobs:
            content = cc.get_blob_client(blob).download_blob().readall()
            items.append(content)

    return items


def summarize_partition(items: typing.List[typing.Dict]) -> pctasks.core.utils.summary.ObjectSummary:
    first, *rest = items
    result = pctasks.core.utils.summary.ObjectSummary.summarize_dict(first)
    for item in rest:
        result = result.merge(pctasks.core.utils.summary.ObjectSummary.summarize_dict(item))
    return result


aggregate = lambda x: functools.reduce(lambda a, b: a.merge(b), x)


@contextlib.contextmanager
def get_compute():
    with dask_kubernetes.operator.KubeCluster(
        namespace="dask",
        image="pccomponents.azurecr.io/pctasks-dask:2023.4.13.0",
        resources={
            "requests": {"memory": "7Gi", "cpu": "0.9"},
            "limit": {"memory": "8Gi", "cpu": "1"}
        },
    ) as cluster:
        with cluster.get_client() as client:
            cluster.scale(8)
            print(client.dashboard_link)
            yield client


def summarize(prefix, depth, storage_options):
    """
    prefix="OLCI/OL_2_LFR___/", depth=5
    """
    with get_compute():
        logger.info("Listing prefixes. prefix=%s", prefix)
        prefixes = list_prefixes(prefix, depth, storage_options).compute()
        logger.info("prefix_count=%d", len(prefixes))
        bag = dask.bag.from_delayed([read_prefix(x, storage_options) for x in prefixes]).map(json.loads)
        summary = bag.reduction(summarize, aggregate).compute()

    return summary

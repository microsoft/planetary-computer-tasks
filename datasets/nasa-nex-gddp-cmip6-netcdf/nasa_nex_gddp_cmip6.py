# Basic plan: reuse as much of Collection as we can.
#
# Thanks to the layout on in Blob Storage, the asset_uri will be something
# 'NEX/GDDP-CMIP6/ACCESS-CM2/historical/' There are 104 of those {model,
# scenario} pairs. Each prefix will result in ~65 - 86 items, depending
# on which variables are produced for that combination and the number
# of years covered by that scenario.
# Each of these items will take a while to create (minutes...)
# so having a chunksize of 1 is fine.

import gc
import sys
import time
import logging

import pystac

from pctasks.core.storage import StorageFactory
from pctasks.dataset.collection import Collection
from pctasks.core.models.base import PCBaseModel

import itertools

import adlfs
import xarray as xr
import azure.storage.blob
import azure.identity.aio
from stactools.nasa_nex_gddp_cmip6 import stac
import json
import string
from typing import Generator

import fsspec
import azure.storage.blob
import azure.identity
import kerchunk.hdf
import kerchunk.combine
import planetary_computer

from pctasks.task.task import Task
from pctasks.task.context import TaskContext


logger = logging.getLogger(__name__)


class ItemSpec(PCBaseModel):
    """
    Representation of the assets associated with an Item.

    `item_id` is the unique identifier for the item. Everything other
    field is a path to the asset in Blob Storage (the name).

    This is needed because

    1. The actual files are dynamic (depending on which model/scenario
       has updated v1.1 or v1.2 assets)
    2. The prefix we're listing under has many items.
    """

    item_id: str
    pr: str
    tas: str
    rlds: str
    rsds: str
    sfcWind: str
    hurs: str | None = None
    huss: str | None = None
    tasmax: str | None = None
    tasmin: str | None = None


def item_key(x: tuple[str, stac.Parts]) -> str:
    _, parts = x
    return parts.item_id


def asset_key(x: tuple[str, stac.Parts]) -> str:
    return x[0].split("/")[-1].split("_")[0]


def version_key(x: tuple[str, stac.Parts]) -> str:
    return x[1].version


def list_item_specs(
    prefix: str, container_client: azure.storage.blob.ContainerClient
) -> list[ItemSpec]:
    # prefix ix like NEX/GDDP-CMIP6/ACCESS-CM2/historical/
    blobs = list(container_client.list_blobs(prefix))
    item_specs = build_item_spec(blobs)
    return item_specs


def build_item_spec(blobs: list[azure.storage.blob.BlobProperties]) -> list[ItemSpec]:
    blobs = [x for x in blobs if x.size > 0]
    names = [x.name for x in blobs]
    parts = [stac.Parts.from_path(name) for name in names]

    pairs = list(zip(names, parts))
    by_item = {
        k: list(v) for k, v in itertools.groupby(sorted(pairs, key=item_key), item_key)
    }
    item_specs = []

    for k, v in by_item.items():
        d = {
            k: max(v, key=version_key)[0]
            for k, v in itertools.groupby(sorted(v, key=asset_key), key=asset_key)
        }
        item_specs.append(ItemSpec(item_id=k, **d))
    return item_specs


def read_dataset(
    item_spec: ItemSpec, fs: adlfs.AzureBlobFileSystem, container_name: str
) -> xr.Dataset:
    # open the datasets
    data_vars = item_spec.dict()
    data_vars.pop("item_id")

    datasets = []
    for var, name in data_vars.items():
        if name is None:
            # Some models are missing some variables
            continue

        # See https://github.com/h5py/h5py/issues/2019 for the gc stuff
        gc.disable()
        logger.info("Reading variable. item_id=%s, variable=%s", item_spec.item_id, var)
        ds = xr.open_dataset(fs.open(f"{container_name}/{name}"), engine="h5netcdf")
        gc.enable()
        source = "/".join([fs.account_url, container_name, name])
        ds[var].encoding["source"] = source
        datasets.append(ds)

    ds = xr.merge(datasets, join="exact")
    return ds


class NASANEXGDDPCMIP6Collection(Collection):
    limit: int | None = None

    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> list[pystac.Item]:
        # asset_uri should be a prefix like:
        #   blob://nasagddp/nex-gddp-cmip6/NEX/GDDP-CMIP6/ACCESS-CM2/historical/r1i1p1f1
        # fsspec_uri = as
        *_, account_name, container_name, path = asset_uri.split("/", 4)
        container_client = azure.storage.blob.ContainerClient(
            f"https://{account_name}.blob.core.windows.net",
            container_name,
            azure.identity.DefaultAzureCredential(),
        )
        fs = adlfs.AzureBlobFileSystem(
            account_name, credential=azure.identity.aio.DefaultAzureCredential()
        )
        item_specs = list_item_specs(path, container_client)
        items = []
        N = len(item_specs)

        for i, item_spec in enumerate(item_specs, 1):
            if item_spec.item_id.split(".")[0] in {"GISS-E2-1-G"}:
                logger.info(
                    "Item has misaligned coordinates. Skipping. id=%s",
                    item_spec.item_id,
                )
                continue

            t0 = time.monotonic()
            logger.info("Creating item. id=%s", item_spec.item_id)
            ds = read_dataset(item_spec, fs, container_name)
            item = stac.create_item_from_dataset(ds)
            t1 = time.monotonic()
            logger.info(
                "Created item. id=%s. time=%0.2f, [%d/%d]",
                item_spec.item_id,
                t1 - t0,
                i,
                N,
            )
            items.append(item)
            if cls.limit is not None and i >= cls.limit:
                break

        return items


# --------------------------------------------------------------------------------------
# Kerchunk Stuff
# Throwing in here to simplify packaging.


def make_templates(all_urls: list[str]) -> Generator[str, None, None]:
    N = len(string.ascii_letters)
    i = 0

    while i < len(all_urls):
        n = (i // N) + 1
        for tup in itertools.combinations_with_replacement(string.ascii_letters, n):
            id_ = "".join(tup)
            yield "{{" + id_ + "}}"
            i += 1


def make_timeseries(urls: list[str]) -> dict:
    gen = make_templates(urls)
    urls_to_templates = {url: template for url, template in zip(urls, gen)}
    templates_to_urls = {template: url for url, template in urls_to_templates.items()}
    templates = {k[2:-2]: v.split("?")[0] for k, v in templates_to_urls.items()}

    translated = []
    for url in urls:
        # Some (all?) versions of h5netcdf / h5py / fsspec can deadlocks
        # when reading files over the network.
        # See https://github.com/h5py/h5py/issues/2019 for background.
        # https://github.com/TomAugspurger/httpfile for an alternative.
        print("Reading", url.split("?")[0], file=sys.stderr)
        signed_url = planetary_computer.sign(url)

        with fsspec.open(signed_url) as inf:
            h5chunks = kerchunk.hdf.SingleHdf5ToZarr(inf, signed_url)
            tr = h5chunks.translate()
            translated.append(tr)

    mzz = kerchunk.combine.MultiZarrToZarr(
        translated,
        remote_protocol="https",
        concat_dims=["time"],
    )
    d = mzz.translate()

    # We use templates to reduce the size of the JSON and make
    # planetary_computer.sign work
    d["templates"] = templates
    for _, ref in d["refs"].items():
        if (
            isinstance(ref, list)
            and len(ref) == 3
            and ref[0].split("?")[0] in urls_to_templates
        ):
            template = urls_to_templates[ref[0].split("?")[0]]
            ref[0] = template

    return d


class ListInputsInput(PCBaseModel):
    prefix: str


class ListInputsOutput(PCBaseModel):
    asset_uris: list[str]


class ListInputsTask(Task[ListInputsInput, ListInputsOutput]):
    _input_model = ListInputsInput
    _output_model = ListInputsOutput

    def run(self, input: ListInputsInput, context: TaskContext) -> ListInputsOutput:
        storage, path = context.storage_factory.get_storage_for_file(input.prefix)
        prefix, models, _ = list(storage.walk(name_starts_with=path, max_depth=2))[0]

        asset_uris = []

        for model in models:
            for _, scenarios, _ in storage.walk(
                name_starts_with=f"{prefix}{model}/", max_depth=3
            ):
                if "historical" in scenarios:
                    for _, rthings, _ in storage.walk(
                        name_starts_with=f"{prefix}{model}/historical/", max_depth=4
                    ):
                        assert len(rthings) == 1
                        rthing = rthings[0]
                        print(model, rthing, file=sys.stderr)
                        asset_uris.append(
                            storage.get_uri(f"{prefix}{model}/historical/{rthing}")
                        )

        return ListInputsOutput(asset_uris=asset_uris)


class KerchunkInput(PCBaseModel):
    # A path like 'blob://nasagddp/nex-gddp-cmip6/NEX/GDDP-CMIP6/ACCESS-CM2/historical/r1i1p1f1'
    # Only works for "historical"
    asset_uri: str
    references_prefix: str = "blob://nasagddp/nex-gddp-cmip6-references"


class KerchunkOutput(PCBaseModel):
    references_uri: str


class KerchunkTask(Task[KerchunkInput, KerchunkOutput]):
    _input_model = KerchunkInput
    _output_model = KerchunkOutput

    def run(self, input: KerchunkInput, context: TaskContext):
        result = run_kerchunk(input.asset_uri)
        *_, model, scenario, _ = input.asset_uri.split("/")
        output = (
            f"b{input.references_prefix.rstrip('/')}/{model}_{scenario}.json"
        )

        # output name needs to be derived from the input.
        dest_storage, dest_path = context.storage_factory.get_storage_for_file(output)
        dest_storage.write_text(dest_path, json.dumps(result))
        return KerchunkOutput(references_uri=dest_path)


def run_kerchunk(asset_uri: str) -> dict:
    account_name = "nasagddp"
    container_name = "nex-gddp-cmip6"

    *_, account_name, container_name, path = asset_uri.split("/", 4)
    container_client = azure.storage.blob.ContainerClient(
        f"https://{account_name}.blob.core.windows.net",
        container_name,
        azure.identity.DefaultAzureCredential(),
    )
    item_specs = list_item_specs(path, container_client)
    account_url = f"https://{account_name}.blob.core.windows.net"

    all_urls = [
        f"{account_url}/{container_name}/{v}"
        for item_spec in item_specs
        for k, v in item_spec.dict().items()
        if k != "item_id"
    ]

    refs = make_timeseries(all_urls)
    return refs

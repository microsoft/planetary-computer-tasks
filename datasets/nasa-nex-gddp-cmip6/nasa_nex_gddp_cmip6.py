from typing import List, Union
import planetary_computer
from collections import namedtuple

import io
import pystac

from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory
from pctasks.dataset.collection import Collection

from operator import itemgetter
from string import ascii_lowercase
import itertools

from kerchunk.combine import MultiZarrToZarr
from kerchunk.hdf import SingleHdf5ToZarr
from kerchunk.netCDF3 import NetCDF3ToZarr
from kerchunk.utils import rename_target

import adlfs
import xarray as xr
import xstac

class Cmip6Collection(Collection):
    def get_item(cls, paths, range_compress=False):
        credential = planetary_computer.sas.get_token("nasagddp", "nex-gddp-cmip6").token
        fs = adlfs.AzureBlobFileSystem("nasagddp", credential=credential)
        template = pystac.Item(
            "item",
            geometry={
                "type": "Polygon",
                "coordinates": [
                    [
                        [180.0, -90.0],
                        [180.0, 90.0],
                        [-180.0, 90.0],
                        [-180.0, -90.0],
                        [180.0, -90.0],
                    ]
                ],
            },
            bbox=[-180, -90, 180, 90],
            datetime=None,
            properties={"start_datetime": None, "end_datetime": None},
        )

        datasets = [xr.open_dataset(fs.open(path)) for path in paths]
        ds = xr.merge(datasets)
        r = xstac.xarray_to_stac(ds, template, reference_system=4326)
        r.id = '.'.join(itemgetter(0,1,3)(cls.path_to_item_id(cls, paths[0]).split('.')))
        for path in paths:
            var_name = path.split("/")[6]
            asset = pystac.Asset(
                f"https://nasagddp.blob.core.windows.net/{path}",
                media_type="application/netcdf",
                roles=["data"],
                extra_fields={"cmip6:variable": var_name}
            )
            r.add_asset(var_name, asset)
        metadata = cls.create_multifile_indices(cls, paths, range_compress, ds=ds)
        r.properties["kerchunk:indices"] = metadata
        parts = cls.split_path(cls, paths[0])

        for k, v in parts._asdict().items():
            if 'variable' in k: continue
            r.properties[f"cmip6:{k}"] = v
        return r

    def iter_all_strings(self):
        for size in itertools.count(1):
            for s in itertools.product(ascii_lowercase, repeat=size):
                yield "".join(s)
            
    def split_path(cls, path):
        _, _, _, model, scenario, _, variable, file = path.split("/")
        year = int(file.split(".")[0].split("_")[-1])
        Parts = namedtuple("Parts", "model scenario variable year")
        return Parts(model, scenario, variable, year)


    def path_to_item_id(cls, path):
        """
        Item IDs are {model}.{scenario}.{variable}.{year}
        """
        p = cls.split_path(cls, path)
        return ".".join(list(map(str, p)))


    def create_multifile_indices(cls, paths,range_compress=False,ds=None):
        single_ref_sets = []
        for path in paths:
            credential = planetary_computer.sas.get_token("nasagddp", "nex-gddp-cmip6").token
            fs = adlfs.AzureBlobFileSystem("nasagddp", credential=credential)
            with fs.open(path) as f:
                f = f.read()
                metadata = None
                if b'CDF' in f[:3]:
                    fname = '{}.nc'.format(uuid.uuid4())
                    with open(fname, 'wb') as f:
                        f.write(file)
                    h5chunks = NetCDF3ToZarr(fname)
                    metadata = h5chunks.translate()
                    for key in metadata['refs']:
                        if len(metadata['refs'][key]) == 3:
                            if metadata['refs'][key][0] == fname:
                                metadata['refs'][key][0] = f"https://nasagddp.blob.core.windows.net/{path}"
                    os.remove(fname)
                    single_ref_sets += [metadata]
                elif b'HDF' in f[:10]:
                    h5chunks = SingleHdf5ToZarr(io.BytesIO(f), f"https://nasagddp.blob.core.windows.net/{path}")
                    metadata = h5chunks.translate()
                    single_ref_sets += [metadata]
                else:
                    print('Type', file[:10], 'is not yet supported.')
        mzz = MultiZarrToZarr(single_ref_sets, concat_dims=['time'], identical_dims=['lat','lon'])
        metadata = mzz.translate()
        templates = {}
        keys = [s for s in itertools.islice(cls.iter_all_strings(cls), len(paths))]
        for key, path in zip(keys, paths):
            templates[key] = "https://nasagddp.blob.core.windows.net/{}".format(path)
            metadata = rename_target(metadata, {"https://nasagddp.blob.core.windows.net/{}".format(path):"{{" + key + "}}"})
        metadata['templates'] = templates
        if range_compress:
            metadata['refs']['lat/0'] = 'base64:' + base64.b64encode(Range().encode(ds.lat.values)).decode()
            metadata['refs']['lon/0'] = 'base64:' + base64.b64encode(Range().encode(ds.lon.values)).decode()
            metadata['refs']['time/0'] = 'base64:' + base64.b64encode(Range().encode(ds.time.values)).decode()
            metadata['refs']['lat/.zarray'] = json.dumps({k:None if 'compress' in k else [{'id':'range'}] if 'filter' in k else
                                                          v for k,v in json.loads(metadata['refs']['lat/.zarray']).items()})
            metadata['refs']['lon/.zarray'] = json.dumps({k:None if 'compress' in k else [{'id':'range'}] if 'filter' in k else
                                                          v for k,v in json.loads(metadata['refs']['lon/.zarray']).items()})
            metadata['refs']['time/.zarray'] = json.dumps({k:None if 'compress' in k else [{'id':'range'}] if 'filter' in k else
                                                           json.loads(metadata['refs']['time/.zarray'])['shape'] if 'chunk' in k else
                                                           v for k,v in json.loads(metadata['refs']['time/.zarray']).items()})
        return metadata
    
    def get_var(cls, dataset_name):
        #'rsds' variable shared by all. Can use matches in dataset.yaml as filter
        if dataset_name in set(['GISS-E2-1-G', 'GFDL-CM4', 'NorESM2-LM', 'CMCC-ESM2', 'CanESM5',
                                'NorESM2-MM', 'EC-Earth3', 'CMCC-CM2-SR5', 'INM-CM4-8', 'MPI-ESM1-2-LR',
                                'FGOALS-g3', 'ACCESS-CM2', 'MIROC-ES2L', 'CNRM-CM6-1', 'HadGEM3-GC31-LL',
                                'KACE-1-0-G', 'GFDL-ESM4', 'INM-CM5-0', 'KIOST-ESM', 'MPI-ESM1-2-HR',
                                'HadGEM3-GC31-MM', 'UKESM1-0-LL', 'GFDL-CM4_gr2', 'CNRM-ESM2-1', 'TaiESM1',
                                'ACCESS-ESM1-5', 'MRI-ESM2-0', 'EC-Earth3-Veg-LR']): 
            return 'rsds', ['hurs', 'huss', 'pr', 'rlds', 'rsds', 'sfcWind', 'tas', 'tasmax', 'tasmin']
        elif dataset_name in set(['BCC-CSM2-MR']):
            return 'rsds', ['huss', 'pr', 'rlds', 'rsds', 'sfcWind', 'tas', 'tasmax', 'tasmin']
        elif dataset_name in set(['IITM-ESM', 'CESM2-WACCM', 'CESM2']):
             return 'rsds', ['hurs', 'huss', 'pr', 'rlds', 'rsds', 'sfcWind', 'tas']
        elif dataset_name in set(['MIROC6', 'IPSL-CM6A-LR']):
            return 'rsds', ['hurs', 'pr', 'rlds', 'rsds', 'sfcWind', 'tas', 'tasmax', 'tasmin']
        elif dataset_name in set(['NESM3']):
            return 'rsds', ['pr', 'rlds', 'rsds', 'sfcWind', 'tas', 'tasmax', 'tasmin']
        else:
            return 'ERROR', ['ERROR']
    
    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[pystac.Item], WaitTaskResult]:
        asset_storage, asset_path = storage_factory.get_storage_for_file(asset_uri)
        href = asset_path
        part1, part2, dataset_name, scenario, part5, var, fname = href.split('/')
        year = fname.split("_")[-1].split(".")[0]
        
        fname_template = "_".join(["{}"] + fname.split("_")[1:])
        pass_var, variables = cls.get_var(cls, dataset_name)
        
        if var != pass_var:
            return []
        
        #Deal with corrupt files KIOST-ESM_ssp245_2058
        if 'KIOST-ESM' in dataset_name and 'ssp245' in scenario and '2058' in year:
            return []
        
        paths = ['/'.join([asset_storage.container_name, part1, part2, dataset_name, scenario, part5, var, fname_template.format(var)]) for var in variables]
        item = cls.get_item(cls, paths)
        return [item]
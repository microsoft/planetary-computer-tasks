from importlib.metadata import files
import adlfs
import planetary_computer
from pystac import Collection

collection = Collection.from_file(
    "https://planetarycomputer.microsoft.com/api/stac/v1/collections/aster-l1t"
)
asset = planetary_computer.sign(collection.assets["geoparquet-items"])
filesystem = adlfs.AzureBlobFileSystem(**asset.extra_fields["table:storage_options"])
for path in filesystem.ls("items/aster-l1t.parquet"):
    print(path)

# planetary-computer-tasks dataset: goes-cmi

GOES Cloud & Moisture Imagery

## Notes

- There is no data in Azure container for GOES-17 after January 10th:
    - GOES-17 was moved to 105 degrees west longitude on January 12, 2023, and now serves as a backup to the operational GOES constellation.
    - source: https://www.goes-r.gov/users/GOES-17-ABI-Performance.html
- Not replicating `handle_duplicates` from ETL. Handling duplicates appears to be an ETL feature that was not ported to pctasks.
- If an exception is caught in the `create_item` method, an error message with the exception info is logged and an empty list is returned. This is in lieu of ETL's behaviour of returning an error record, which is not supported by pctasks.
- `GoesCmiCollection` was ported as faithfully as possible from ETL. The complexity is inherited from ETL.

## Building the Docker image

- To build and push a custom docker image to our container registry:

    ```shell
    az acr build -r {the registry} --subscription {the subscription} -t pctasks-goes-cmi:latest -t pctasks-goes-cmi:{date}.{count} -f datasets/goes/goes-cmi/Dockerfile .
    ```

- Note L32 in the Dockerfile. It pins Python, gdal, and numpy to older versions. Using Python=3.11 and unpinned gdal and numpy did not work for creating COGs in the Web Mercator (epsg:3857) projection.
- Note the --force-reinstall --no-binary of rasterio on L70, which cleaned up some rasterio errors.

## Extra args

The `dataset.yaml` is expecting an extra argument named `extra-prefix` to be included in the pctasks call to filter chunk creation:

`--arg extra-prefix "{year}/"`
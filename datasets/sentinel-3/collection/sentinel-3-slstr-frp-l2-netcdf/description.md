This Collection provides Sentinel-3 [SLSTR Level-2 Fire Radiative Power](https://sentinel.esa.int/web/sentinel/user-guides/sentinel-3-slstr/product-types/level-2-frp) (FRP) products containing data on fires detected over land and ocean.

## Data files

The primary measurement data is contained in the `FRP_in.nc` file and provides FRP and uncertainties, projected onto a 1km grid, for fires detected in the thermal infrared (TIR) spectrum over land. Since February 2022, FRP and uncertainties are also provided for fires detected in the short wave infrared (SWIR) spectrum over both land and ocean, with the delivered data projected onto a 500m grid. The latter SWIR-detected fire data is only available for night-time measurements and is contained in the `FRP_an.nc` or `FRP_bn.nc` files.

In addition to the measurement data files, a standard set of annotation data files provide meteorological information, geolocation and time coordinates, geometry information, and quality flags.

## Processing

The TIR fire detection is based on measurements from the S7 and F1 bands of the [SLSTR instrument](https://sentinels.copernicus.eu/web/sentinel/technical-guides/sentinel-3-slstr/instrument); SWIR fire detection is based on the S5 and S6 bands. More information about the product and data processing can be found in the [User Guide](https://sentinel.esa.int/web/sentinel/user-guides/sentinel-3-slstr/product-types/level-2-frp) and [Technical Guide](https://sentinel.esa.int/web/sentinel/technical-guides/sentinel-3-slstr/level-2/frp-processing).

This Collection contains Level-2 data in NetCDF files from August 2020 to present.

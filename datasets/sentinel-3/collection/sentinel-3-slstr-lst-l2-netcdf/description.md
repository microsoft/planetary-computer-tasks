This collection provides [SLSTR Level-2 Land Surface Temperature](https://sentinel.esa.int/web/sentinel/user-guides/sentinel-3-slstr/product-types/level-2-lst) (LST) products containing data on temperature measurements on a 1km grid.

## Data files

The dataset includes data on the primary measurement variable, land surface temperature, in a single NetCDF file. A second NetCDF file contains several ancillary variables:

- Normalized Difference Vegetation Index
- Surface biome classification
- Fractional vegetation cover
- Total water vapor column

In addition to the primary and ancillary data files, a standard set of annotation data files provide meteorological information, geolocation and time coordinates, geometry information, and quality flags.

## Processing overview

The collection contains Level-2 data in NetCDF files. Radiance is measured in two channels to determine the temperature of the Earth's surface skin in the instrument field of view, where the term 'skin' refers to the top surface of bare soil or the effective emitting temperature of vegetation canopies as viewed from above. See the [processing overview](https://sentinel.esa.int/web/sentinel/technical-guides/sentinel-3-slstr/level-2/lst-processing) for more.

## STAC Item geometries

This collection contains small "chips" and long "stripes" of data collected along the satellite direction of travel. Approximately five percent of the STAC Items describing long stripes of data contain geometries that encompass a larger area than an exact concave hull of the data extents. This may require additional filtering when searching the collection for Items that spatially intersect an area of interest.

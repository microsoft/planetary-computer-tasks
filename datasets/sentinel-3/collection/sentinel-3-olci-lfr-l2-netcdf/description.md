This collection provides the Full Resolution [OLCI Level-2 Land][olci-l2] products containing data on global vegetation, chlorophyll, and water vapor.

## Data files

This dataset includes data on three primary variables:

* OLCI global vegetation index file
* terrestrial Chlorophyll index file
* integrated water vapor over water file.

Each variable is contained within a separate NetCDF file, and is cataloged as an asset in each Item.

Several associated variables are also provided in the annotations data files:

* rectified reflectance for red and NIR channels (RC681 and RC865)
* classification, quality and science flags (LQSF)
* common data such as the ortho-geolocation of land pixels, solar and satellite
  angles, atmospheric and meteorological data, time stamp or instrument
  information. These variables are inherited from Level-1B products.

The full resolution product offers a spatial sampling of approximately 300 m.

## Processing overview

This collection contains Level-2 data in NetCDF files. The values in the data files have been
converted from Top of Atmosphere radiance to reflectance, and includes various corrections for gaseous absorption and pixel classification.
See [processing overview](https://sentinel.esa.int/web/sentinel/technical-guides/sentinel-3-olci/level-2/processing) for more.

[olci-l2]: https://sentinel.esa.int/web/sentinel/technical-guides/sentinel-3-olci/level-2/land-products

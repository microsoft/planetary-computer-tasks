This collection provides Sentinel-3 Full Resolution [OLCI Level-2 Land][olci-l2] products containing data on global vegetation, chlorophyll, and water vapor.

## Data files

This dataset includes data on three primary variables:

* OLCI global vegetation index file
* terrestrial Chlorophyll index file
* integrated water vapor over water file.

Each variable is contained within a separate NetCDF file, and is cataloged as an asset in each Item.

Several associated variables are also provided in the annotations data files:

* rectified reflectance for red and NIR channels (RC681 and RC865)
* classification, quality and science flags (LQSF)
* common data such as the ortho-geolocation of land pixels, solar and satellite angles, atmospheric and meteorological data, time stamp or instrument information. These variables are inherited from Level-1B products.

This full resolution product offers a spatial sampling of approximately 300 m.

## Processing overview

The values in the data files have been converted from Top of Atmosphere radiance to reflectance, and include various corrections for gaseous absorption and pixel classification. More information about the product and data processing can be found in the [User Guide](https://sentinel.esa.int/web/sentinel/user-guides/sentinel-3-olci/product-types/level-2-land) and [Technical Guide](https://sentinel.esa.int/web/sentinel/technical-guides/sentinel-3-olci/level-2/processing).

This Collection contains Level-2 data in NetCDF files from April 2016 to present.

[olci-l2]: https://sentinel.esa.int/web/sentinel/technical-guides/sentinel-3-olci/level-2/land-products

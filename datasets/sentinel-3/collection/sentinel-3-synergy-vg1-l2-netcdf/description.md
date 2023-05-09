This Collection provides the Sentinel-3 [Synergy Level-2 1-Day Surface Reflectance and NDVI](https://sentinels.copernicus.eu/web/sentinel/user-guides/sentinel-3-synergy/product-types/level-2-vg1-v10) products, which are SPOT VEGETATION Continuity Products similar to those obtained from the [VEGETATION instrument](https://docs.terrascope.be/#/Satellites/SPOT-VGT/MissionInstruments) onboard the SPOT-4 and SPOT-5 satellites. The primary variables are a maximum Normalized Difference Vegetation Index (NDVI) composite, which is derived from daily ground reflecrtance, and four surface reflectance bands:

- B0 (Blue, 450nm)
- B2 (Red, 645nm)
- B3 (NIR, 835nm)
- MIR (SWIR, 1665nm)

The four reflectance bands have center wavelengths matching those on the original SPOT VEGETATION instrument. The NDVI variable, which is an indicator of the amount of vegetation, is derived from the B3 and B2 bands.

## Data files

The four reflectance bands and NDVI values are each contained in dedicated NetCDF files. Additional metadata are delivered in annotation NetCDF files, each containing a single variable, including the geometric viewing and illumination conditions, the total water vapour and ozone columns, and the aerosol optical depth.

Each 1-day product is delivered as a set of 10 rectangular scenes:

- AFRICA
- NORTH_AMERICA
- SOUTH_AMERICA
- CENTRAL_AMERICA
- NORTH_ASIA
- WEST_ASIA
- SOUTH_EAST_ASIA
- ASIAN_ISLANDS
- AUSTRALASIA
- EUROPE

More information about the product and data processing can be found in the [User Guide](https://sentinels.copernicus.eu/web/sentinel/user-guides/sentinel-3-synergy/product-types/level-2-vg1-v10) and [Technical Guide](https://sentinel.esa.int/web/sentinel/technical-guides/sentinel-3-synergy/vgt-s/vg1-product-surface-reflectance).

This Collection contains Level-2 data in NetCDF files from October 2018 to present.

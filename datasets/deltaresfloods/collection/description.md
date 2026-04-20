[Deltares](https://www.deltares.nl/en/) has produced inundation maps of flood depth using a model that takes into account water level attenuation and is forced by sea level. At the coastline, the model is forced by extreme water levels containing surge and tide from GTSMip6. The water level at the coastline is extended landwards to all areas that are hydrodynamically connected to the coast following a ‘bathtub’ like approach and calculates the flood depth as the difference between the water level and the topography. Unlike a simple 'bathtub' model, this model attenuates the water level over land with a maximum attenuation factor of 0.5 m km-1. The attenuation factor simulates the dampening of the flood levels due to the roughness over land.

In its current version, the model does not account for varying roughness over land and permanent water bodies such as rivers and lakes, and it does not account for the compound effects of waves, rainfall, and river discharge on coastal flooding. It also does not include the mitigating effect of coastal flood protection. Flood extents must thus be interpreted as the area that is potentially exposed to flooding without coastal protection.

See the complete [methodology documentation](https://ai4edatasetspublicassets.blob.core.windows.net/assets/aod_docs/11206409-003-ZWS-0003_v0.1-Planetary-Computer-Deltares-global-flood-docs.pdf) for more information.

## Digital elevation models (DEMs)

This documentation will refer to three DEMs:

* `NASADEM` is the SRTM-derived [NASADEM](https://planetarycomputer.microsoft.com/dataset/nasadem) product.
* `MERITDEM` is the [Multi-Error-Removed Improved Terrain DEM](http://hydro.iis.u-tokyo.ac.jp/~yamadai/MERIT_DEM/), derived from SRTM and AW3D.
* `LIDAR` is the [Global LiDAR Lowland DTM (GLL_DTM_v1)](https://data.mendeley.com/datasets/v5x4vpnzds/1).

## Global datasets

This collection includes multiple global flood datasets derived from three different DEMs (`NASA`, `MERIT`, and `LIDAR`) and at different resolutions. Not all DEMs have all resolutions:

* `NASADEM` and `MERITDEM` are available at `90m` and `1km` resolutions
* `LIDAR` is available at `5km` resolution

## Historic event datasets

This collection also includes historical storm event data files that follow similar DEM and resolution conventions. Not all storms events are available for each DEM and resolution combination, but generally follow the format of:

`events/[DEM]_[resolution]-wm_final/[storm_name]_[event_year]_masked.nc`

For example, a flood map for the MERITDEM-derived 90m flood data for the "Omar" storm in 2008 is available at:

<https://deltaresfloodssa.blob.core.windows.net/floods/v2021.06/events/MERITDEM_90m-wm_final/Omar_2008_masked.nc>

## Contact

For questions about this dataset, contact [`aiforearthdatasets@microsoft.com`](mailto:aiforearthdatasets@microsoft.com?subject=deltares-floods%20question).
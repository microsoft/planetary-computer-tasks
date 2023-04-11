# Sentinel-3

## Dataset structure

This dataset has many different products. We create one STAC collection per product. The collections are under the `collection` folder.

```
collection/sentinel-3-olci-lfr-l2-netcdf
collection/sentinel-3-olci-wfr-l2-netcdf
collection/sentinel-3-slstr-frp-l2-netcdf
collection/sentinel-3-slstr-lst-l2-netcdf
collection/sentinel-3-slstr-wst-l2-netcdf
collection/sentinel-3-sral-lan-l2-netcdf
collection/sentinel-3-sral-wat-l2-netcdf
collection/sentinel-3-synergy-aod-l2-netcdf
collection/sentinel-3-synergy-syn-l2-netcdf
collection/sentinel-3-synergy-v10-l2-netcdf
collection/sentinel-3-synergy-vg1-l2-netcdf
collection/sentinel-3-synergy-vgp-l2-netcdf
```

The package `sentinel_3` contains the python code for making the STAC items.
Each collection has its own module
(`sentinel_3/sentinel_3_olci_lfr_l2_netcdf.py`). The name of the module should
match the name of the collection. The module should have a class named
`Collection` that is the pctasks `dataset.Collection` subclass.
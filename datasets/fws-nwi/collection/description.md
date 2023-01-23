The Wetlands Data Layer is the product of over 45 years of work by the National Wetlands Inventory (NWI) and its collaborators and currently contains more than 35 million wetland and deepwater features. This dataset, covering the conterminous United States, Hawaii, Puerto Rico, the Virgin Islands, Guam, the major Northern Mariana Islands and Alaska, continues to grow at a rate of 50 to 100 million acres annually as data are updated.

**NOTE:** Due to the variation in use and analysis of this data by the end user, each  state's wetlands data extends beyond the state boundary. Each state includes wetlands data that intersect the 1:24,000 quadrangles that contain part of that state (1:2,000,000 source data). This allows the user to clip the data to their specific analysis datasets. Beware that two adjacent states will contain some of the same data along their borders.

For more information, visit the National Wetlands Inventory [homepage](https://www.fws.gov/program/national-wetlands-inventory).

## STAC Metadata

In addition to the `zip` asset in every STAC item, each item has its own assets unique to its wetlands. In general, each item will have several assets, each linking to a [geoparquet](https://github.com/opengeospatial/geoparquet) asset with data for the entire region or a sub-region within that state. Use the `cloud-optimized` [role](https://github.com/radiantearth/stac-spec/blob/master/item-spec/item-spec.md#asset-roles) to select just the geoparquet assets. See the Example Notebook for more.
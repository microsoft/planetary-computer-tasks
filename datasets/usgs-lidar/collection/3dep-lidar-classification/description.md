This collection is derived from the [USGS 3DEP COPC collection](https://planetarycomputer.microsoft.com/dataset/3dep-lidar-copc). It uses the [ASPRS](https://www.asprs.org/) (American Society for Photogrammetry and Remote Sensing) [Lidar point classification](https://desktop.arcgis.com/en/arcmap/latest/manage-data/las-dataset/lidar-point-classification.htm). See [LAS specification](https://www.ogc.org/standards/LAS) for details.

This COG type is based on the Classification [PDAL dimension](https://pdal.io/dimensions.html) and uses [`pdal.filters.range`](https://pdal.io/stages/filters.range.html) to select a subset of interesting classifications. Do note that not all LiDAR collections contain a full compliment of classification labels.
To remove outliers, the PDAL pipeline uses a noise filter and then outputs the Classification dimension.

The STAC collection implements the [`item_assets`](https://github.com/stac-extensions/item-assets) and [`classification`](https://github.com/stac-extensions/classification) extensions. These classes are displayed in the "Item assets" below. You can programmatically access the full list of class values and descriptions using the `classification:classes` field form the `data` asset on the STAC collection.

Classification rasters were produced as a subset of LiDAR classification categories:

```
0, Never Classified
1, Unclassified
2, Ground
3, Low Vegetation
4, Medium Vegetation
5, High Vegetation
6, Building
9, Water
10, Rail
11, Road
17, Bridge Deck
```

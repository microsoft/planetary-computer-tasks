Bing Maps is releasing open building footprints around the world. We have detected over 999 million buildings from Bing Maps imagery between 2014 and 2021 including Maxar and Airbus imagery. The data is freely available for download and use under ODbL. This dataset complements our other releases.

For more information, see the [GlobalMLBuildingFootprints](https://github.com/microsoft/GlobalMLBuildingFootprints/) repository on GitHub.

## Building footprint creation

The building extraction is done in two stages:

1. Semantic Segmentation – Recognizing building pixels on an aerial image using deep neural networks (DNNs)
2. Polygonization – Converting building pixel detections into polygons

**Stage 1: Semantic Segmentation**

![Semantic segmentation](https://raw.githubusercontent.com/microsoft/GlobalMLBuildingFootprints/main/images/segmentation.jpg)

**Stage 2: Polygonization**

![Polygonization](https://github.com/microsoft/GlobalMLBuildingFootprints/raw/main/images/polygonization.jpg)

## Data assets

The building footprints are provided as a set of [geoparquet](https://github.com/opengeospatial/geoparquet) datasets in [Delta][delta] table format.
The data are partitioned by

1. Region
2. quadkey at [Bing Map Tiles][tiles] level 9

Each `(Region, quadkey)` pair will have one or more geoparquet files, depending on the density of the of the buildings in that area.

Note that older items in this dataset are *not* spatially partitioned. We recommend using data with a processing date
of 2023-04-25 or newer. This processing date is part of the URL for each parquet file and is captured in the STAC metadata
for each item (see below).

## Delta Format

The collection-level asset under the `delta` key gives you the fsspec-style URL
to the Delta table. This can be used to efficiently query for matching partitions
by `Region` and `quadkey`. See the notebook for an example using Python.

## STAC metadata

This STAC collection has one STAC item per region. The `msbuildings:region`
property can be used to filter items to a specific region, and the `msbuildings:quadkey`
property can be used to filter items to a specific quadkey (though you can also search
by the `geometry`).

Note that older STAC items are not spatially partitioned. We recommend filtering on
items with an `msbuildings:processing-date` of `2023-04-25` or newer. See the collection
summary for `msbuildings:processing-date` for a list of valid values.

[delta]: https://delta.io/
[tiles]: https://learn.microsoft.com/en-us/bingmaps/articles/bing-maps-tile-system

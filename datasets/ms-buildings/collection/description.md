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

## STAC metadata

This STAC collection has one STAC item per region. The `msbuildings:region` property can be used to filter items to a specific region.

## Data assets

The building footprints are provided as a set of [geoparquet](https://github.com/opengeospatial/geoparquet) datasets. The data are partitioned at multiple levels. There is one [Parquet dataset](https://arrow.apache.org/docs/python/parquet.html#partitioned-datasets-multiple-files) per region. Regions are partitioned into many parquet files so that each file fits comfortably in memory.
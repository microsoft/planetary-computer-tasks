The [Global Biodiversity Information Facility](https://www.gbif.org) (GBIF) is an international network and data infrastructure funded by the world's governments, providing global data that document the occurrence of species. GBIF currently integrates datasets documenting over 1.6 billion species occurrences.

The GBIF occurrence dataset combines data from a wide array of sources, including specimen-related data from natural history museums, observations from citizen science networks, and automated environmental surveys. While these data are constantly changing at [GBIF.org](https://www.gbif.org), periodic snapshots are taken and made available here. 

Data are stored in [Parquet](https://parquet.apache.org/) format; the Parquet file schema is described below.  Most field names correspond to [terms from the Darwin Core standard](https://dwc.tdwg.org/terms/), and have been interpreted by GBIF's systems to align taxonomy, location, dates, etc.  Additional information may be retrieved using the [GBIF API](https://www.gbif.org/developer/summary).

Please refer to the GBIF [citation guidelines](https://www.gbif.org/citation-guidelines) for information about how to cite GBIF data in publications.. For analyses using the whole dataset, please use the following citation:

> GBIF.org ([Date]) GBIF Occurrence Data [DOI of dataset]

For analyses where data are significantly filtered, please track the datasetKeys used and use a "[derived dataset](https://www.gbif.org/citation-guidelines#derivedDatasets)" record for citing the data.

The [GBIF data blog](https://data-blog.gbif.org/categories/gbif/) contains a number of articles that can help you analyze GBIF data.

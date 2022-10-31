ERA5 is the fifth generation ECMWF atmospheric reanalysis of the global climate
covering the period from January 1950 to present. ERA5 is produced by the
Copernicus Climate Change Service (C3S) at ECMWF.

Reanalysis combines model data with observations from across the world into a
globally complete and consistent dataset using the laws of physics. This
principle, called data assimilation, is based on the method used by numerical
weather prediction centres, where every so many hours (12 hours at ECMWF) a
previous forecast is combined with newly available observations in an optimal
way to produce a new best estimate of the state of the atmosphere, called
analysis, from which an updated, improved forecast is issued. Reanalysis works
in the same way, but at reduced resolution to allow for the provision of a
dataset spanning back several decades. Reanalysis does not have the constraint
of issuing timely forecasts, so there is more time to collect observations, and
when going further back in time, to allow for the ingestion of improved versions
of the original observations, which all benefit the quality of the reanalysis
product.

This dataset was converted to Zarr by [Planet OS](https://planetos.com/).
See [their documentation](https://github.com/planet-os/notebooks/blob/master/aws/era5-pds.md)
for more.

## STAC Metadata

Two types of data variables are provided: "forecast" (`fc`) and "analysis" (`an`).

* An **analysis**, of the atmospheric conditions, is a blend of observations
  with a previous forecast. An analysis can only provide
  [instantaneous](https://confluence.ecmwf.int/display/CKB/Model+grid+box+and+time+step)
  parameters (parameters valid at a specific time, e.g temperature at 12:00),
  but not accumulated parameters, mean rates or min/max parameters.
* A **forecast** starts with an analysis at a specific time (the 'initialization
  time'), and a model computes the atmospheric conditions for a number of
  'forecast steps', at increasing 'validity times', into the future. A forecast
  can provide
  [instantaneous](https://confluence.ecmwf.int/display/CKB/Model+grid+box+and+time+step)
  parameters, accumulated parameters, mean rates, and min/max parameters.

Each [STAC](https://stacspec.org/) item in this collection covers a single month
and the entire globe. There are two STAC items per month, one for each type of data
variable (`fc` and `an`). The STAC items include an `ecmwf:kind` properties to
indicate which kind of variables that STAC item catalogs.

## How to acknowledge, cite and refer to ERA5

All users of data on the Climate Data Store (CDS) disks (using either the web interface or the CDS API) must provide clear and visible attribution to the Copernicus programme and are asked to cite and reference the dataset provider:

Acknowledge according to the [licence to use Copernicus Products](https://cds.climate.copernicus.eu/api/v2/terms/static/licence-to-use-copernicus-products.pdf).

Cite each dataset used as indicated on the relevant CDS entries (see link to "Citation" under References on the Overview page of the dataset entry).

Throughout the content of your publication, the dataset used is referred to as Author (YYYY).

The 3-steps procedure above is illustrated with this example: [Use Case 2: ERA5 hourly data on single levels from 1979 to present](https://confluence.ecmwf.int/display/CKB/Use+Case+2%3A+ERA5+hourly+data+on+single+levels+from+1979+to+present).

For complete details, please refer to [How to acknowledge and cite a Climate Data Store (CDS) catalogue entry and the data published as part of it](https://confluence.ecmwf.int/display/CKB/How+to+acknowledge+and+cite+a+Climate+Data+Store+%28CDS%29+catalogue+entry+and+the+data+published+as+part+of+it).
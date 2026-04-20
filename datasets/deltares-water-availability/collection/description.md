[Deltares](https://www.deltares.nl/en/) has produced a hydrological model approach to simulate historical daily reservoir variations for 3,236 locations across the globe for the period 1970-2020 using the distributed [wflow_sbm](https://deltares.github.io/Wflow.jl/stable/model_docs/model_configurations/) model. The model outputs long-term daily information on reservoir volume, inflow and outflow dynamics, as well as information on upstream hydrological forcing.

They hydrological model was forced with 5 different precipitation products. Two products (ERA5 and CHIRPS) are available at the global scale, while for Europe, USA and Australia a regional product was use (i.e. EOBS, NLDAS and BOM, respectively). Using these different precipitation products, it becomes possible to assess the impact of uncertainty in the model forcing. A different number of basins upstream of reservoirs are simulated, given the spatial coverage of each precipitation product.

See the complete [methodology documentation](https://ai4edatasetspublicassets.blob.core.windows.net/assets/aod_docs/pc-deltares-water-availability-documentation.pdf) for more information.

## Dataset coverages

| Name   | Scale                    | Period    | Number of basins |
|--------|--------------------------|-----------|------------------|
| ERA5   | Global                   | 1967-2020 | 3236             |
| CHIRPS | Global (+/- 50 latitude) | 1981-2020 | 2951             |
| EOBS   | Europe/North Africa      | 1979-2020 | 682              |
| NLDAS  | USA                      | 1979-2020 | 1090             |
| BOM    | Australia                | 1979-2020 | 116              |

## STAC Metadata

This STAC collection includes one STAC item per dataset. The item includes a `deltares:reservoir` property that can be used to query for the URL of a specific dataset.

## Contact

For questions about this dataset, contact [`aiforearthdatasets@microsoft.com`](mailto:aiforearthdatasets@microsoft.com?subject=deltares-floods%20question).
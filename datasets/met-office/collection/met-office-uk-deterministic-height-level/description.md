This collection offers 4 parameters at 33 available height levels (5m to 6000m) from the Met Office UKV 2km deterministic forecast. This is a high-resolution gridded weather forecast for the UK, with a resolution of 0.018 degrees, projected on to a 2km horizontal grid. The data is available as NetCDF files.

Available height levels, in metres (m) above ground, are: 
* 5.0 10.0 20.0 30.0 50.0 75.0 100.0 150.0 200.0 250.0 300.0 400.0 500.0 600.0 700.0 800.0 1000.0 1250.0 1500.0 1750.0 2000.0 2250.0 2500.0 2750.0 3000.0 3250.0 3500.0 3750.0 4000.0 4500.0 5000.0 5500.0 6000.0

## Coverage area
The forecast covers the UK and Ireland, with the following latitude and longitude coordinates for each corner of the included area:
* Southwest: 48.8643°N, 10.6734°W 
* Northwest: 61.3322°N, 13.7254°W 
* Northeast: 61.6102°N, 4.3408°E 
* Southeast: 49.0594°N, 2.4654°E 

## Timesteps
The following time steps are available:
* every hour from 0 to 54 hours (for most parameters, see parameter table for exceptions) 
* every 3 hours from 57 to 120 hours 
 
## Update frequency
There are three lengths of model run, each with its own update frequency:
* The Nowcast-length runs forecast the next 12 hours and are at 0100, 0200, 0400, 0500, 0700, 0800, 1000, 1100, 1300, 1400, 1600, 1700, 1900, 2000, 2200 and 2300 UTC.
* The Short-length runs forecast the next 54 hours and are at 0000, 0600, 0900, 1200, 1800 and 2100 UTC.
* The Medium-Length runs forecast the next 120 hours and are at 0300 and 1500 UTC.

## Archive length and latency

As of December 2025, the archive contains data from December 2023 onwards. Forecasts will continue to be available for at least two years from their data date.

The data is typically available 3-6 hours after the model run time.

## Technical specs
The data is available as NetCDF files. NetCDF (Network Common Data Form) is an interface for array-orientated data access and a library that supports the interface. It is composed of 3 components:
* variables store the data
* dimensions give relevant dimension information for the variables
* attributes provide auxiliary information about the variables or dataset itself

NetCDF is used within the atmospheric and oceanic science communities and is network transparent, allowing for it to be accessed by computers that store integers, characters and floating-point numbers.

Iris supports NetCDF files through reading, writing and handling. Iris implements a model based on the CF conventions, giving a format-agnostic interface for working with data.

[Find further support on using Iris with NetCDF files.](https://scitools-iris.readthedocs.io/en/stable/) 

## Help us improve the data services we offer

[Join the Met Office research panel](https://forms.office.com/Pages/ResponsePage.aspx?id=YYHxF9cgRkeH_VD-PjtmGdxioYGoFbFIkZuB_q8Fb3VUQkoxRVQzTFdUMzNMVzczWVM5VTc3QTY3MC4u) to help us understand how people interact with weather and climate data, uncover challenges and explore opportunities.

## How to cite

UKV 2km deterministic forecast was accessed on DATE from _insert Planetary Computer link_.

## License

British Crown copyright 2023-2025, the Met Office, is licensed under [CC BY-SA](https://creativecommons.org/licenses/by-sa/4.0/deed.en).

## Providers
[Met Office](https://www.metoffice.gov.uk/)
See all datasets managed by [Met Office.](https://registry.opendata.aws/?search=managedBy:met%20office)

## Contact
[servicedesk@metoffice.gov.uk](mailto:servicedesk@metoffice.gov.uk). Service desk is only available Mon – Fri, 09:00 until 17:00 UTC (-1 hour during BST). As a non-operational service we aim to respond to any service support enquiries within 3-5 business days.
The [Project Eclipse](https://www.microsoft.com/en-us/research/project/project-eclipse/) Network is a low-cost air quality sensing network for cities and a research project led by the [Urban Innovation Group]( https://www.microsoft.com/en-us/research/urban-innovation-research/) at Microsoft Research.

Project Eclipse currently includes over 100 locations in Chicago, Illinois, USA.

This network was deployed starting in July, 2021, through a collaboration with the City of Chicago, the Array of Things Project, JCDecaux Chicago, and the Environmental Law and Policy Center as well as local environmental justice organizations in the city. [This talk]( https://www.microsoft.com/en-us/research/video/technology-demo-project-eclipse-hyperlocal-air-quality-monitoring-for-cities/) documents the network design and data calibration strategy.

## Storage resources

Data are stored in [Parquet](https://parquet.apache.org/) files in Azure Blob Storage in the West Europe Azure region, in the following blob container:

`https://ai4edataeuwest.blob.core.windows.net/eclipse`

Within that container, the periodic occurrence snapshots are stored in `Chicago/YYYY-MM-DD`, where `YYYY-MM-DD` corresponds to the date of the snapshot.
Each snapshot contains a sensor readings from the next 7-days in Parquet format starting with date on the folder name YYYY-MM-DD.
Therefore, the data files for the first snapshot are at

`https://ai4edataeuwest.blob.core.windows.net/eclipse/chicago/2022-01-01/data_*.parquet

The Parquet file schema is as described below. 

## Additional Documentation

For details on Calibration of Pm2.5, O3 and NO2, please see [this PDF](https://ai4edatasetspublicassets.blob.core.windows.net/assets/aod_docs/Calibration_Doc_v1.1.pdf).

## License and attribution
Please cite: Daepp, Cabral, Ranganathan et al. (2022) [Eclipse: An End-to-End Platform for Low-Cost, Hyperlocal Environmental Sensing in Cities. ACM/IEEE Information Processing in Sensor Networks. Milan, Italy.](https://www.microsoft.com/en-us/research/uploads/prod/2022/05/ACM_2022-IPSN_FINAL_Eclipse.pdf)

## Contact

For questions about this dataset, contact [`msrurbanops@microsoft.com`](mailto:msrurbanops@microsoft.com?subject=eclipse%20question) 


## Learn more

The [Eclipse Project](https://www.microsoft.com/en-us/research/urban-innovation-research/) contains an overview of the Project Eclipse at Microsoft Research.


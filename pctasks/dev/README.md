# Planetary Computer Tasks: Dev

This component of the PCTasks framework is around working with PCTasks
in a development environment.

### Setting up the development environment

To assist in testing, environment variables need to be set
with Azurite credentials for usage in test utilities
so that Azure Storage can be mocked out. You can use the following
environment:

```
# Queues
export PCTASKS_RUN__QUEUES_ACCOUNT_URL=http://azurite:10001/devstoreaccount1
export PCTASKS_RUN__QUEUES_ACCOUNT_NAME=devstoreaccount1
export PCTASKS_RUN__QUEUES_ACCOUNT_KEY=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==

# Tables
export PCTASKS_RUN__TABLES_ACCOUNT_URL=http://azurite:10002/devstoreaccount1
export PCTASKS_RUN__TABLES_ACCOUNT_NAME=devstoreaccount1
export PCTASKS_RUN__TABLES_ACCOUNT_KEY=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==

# Blobs
export PCTASKS_RUN__BLOB_ACCOUNT_URL=http://azurite:10000/devstoreaccount1
export PCTASKS_RUN__BLOB_ACCOUNT_NAME=devstoreaccount1
export PCTASKS_RUN__BLOB_ACCOUNT_KEY=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==
```

## Azurite setup

You can run

```
pctasks-dev azurite setup
```

To set up Azurite with the necessary queues, tables and containers for development.
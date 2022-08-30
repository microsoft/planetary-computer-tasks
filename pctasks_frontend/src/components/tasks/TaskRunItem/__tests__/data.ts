/* eslint-disable no-template-curly-in-string */

export const TestTaskRuns = {
  "create-splits": {
    links: [
      {
        rel: "log",
        href: "https://pctaskstest-staging.azure-api.net/tasks/runs/b6320d38fcec41a0a959831efc54345f/jobs/create-splits/tasks/create-splits/logs/run.txt",
        type: "text/plain",
        title: "Task log: run.txt",
      },
    ],
    errors: null,
    created: "2022-08-01T16:11:10.896926",
    updated: "2022-07-28T22:53:26.821920",
    run_id: "b6320d38fcec41a0a959831efc54345f",
    job_id: "create-splits",
    task_id: "create-splits",
    status: "completed",
  },
};

export const TestTaskDefinitions = {
  "create-splits": {
    id: "create-splits",
    image: "pccomponentstest.azurecr.io/pctasks-task-base:latest",
    image_key: null,
    code: {
      src: "blob://pctasksteststaging/code/94a127b730b624d935b93fe4cc610de1/io_lulc.py",
      requirements: null,
      pip_options: null,
    },
    task: "io_lulc:NineClassIOCollection.create_splits_task",
    args: {
      inputs: [
        {
          uri: "blob://ai4edataeuwest/io-lulc",
          sas_token: "****",
          chunk_options: {
            chunk_length: 100,
            name_starts_with: "nine-class/",
            ends_with: ".tif",
            list_folders: false,
            chunk_file_name: "uris-list",
            chunk_extension: ".csv",
          },
        },
      ],
      options: {},
    },
    tags: null,
    environment: {
      AZURE_TENANT_ID: "${{ secrets.task-tenant-id }}",
      AZURE_CLIENT_ID: "${{ secrets.task-client-id }}",
      AZURE_CLIENT_SECRET: "${{ secrets.task-client-secret }}",
    },
    schema_version: "1.0.0",
  },
};

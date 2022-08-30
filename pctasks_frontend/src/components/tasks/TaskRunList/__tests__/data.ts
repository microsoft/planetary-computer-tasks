/* eslint-disable no-template-curly-in-string */
export const TestTaskRuns = {
  "process-chunk": [
    {
      links: [
        {
          rel: "log",
          href: "https://pctaskstest-staging.azure-api.net/tasks/runs/b6320d38fcec41a0a959831efc54345f/jobs/process-chunk[0]/tasks/create-items/logs/run.txt",
          type: "text/plain",
          title: "Task log: run.txt",
        },
      ],
      errors: null,
      created: "2022-08-04T15:52:20.466013",
      updated: "2022-07-28T22:57:17.785741",
      run_id: "b6320d38fcec41a0a959831efc54345f",
      job_id: "process-chunk",
      task_id: "create-items",
      status: "completed",
    },
    {
      links: [
        {
          rel: "log",
          href: "https://pctaskstest-staging.azure-api.net/tasks/runs/b6320d38fcec41a0a959831efc54345f/jobs/process-chunk[0]/tasks/ingest-items/logs/run.txt",
          type: "text/plain",
          title: "Task log: run.txt",
        },
      ],
      errors: null,
      created: "2022-08-04T15:52:20.466062",
      updated: "2022-07-28T23:01:04.679502",
      run_id: "b6320d38fcec41a0a959831efc54345f",
      job_id: "process-chunk",
      task_id: "ingest-items",
      status: "completed",
    },
  ],
};

export const TestJobTasks = {
  "process-chunk": [
    {
      id: "create-items",
      image: "pccomponentstest.azurecr.io/pctasks-task-base:latest",
      image_key: null,
      code: {
        src: "blob://pctasksteststaging/code/94a127b730b624d935b93fe4cc610de1/io_lulc.py",
        requirements: null,
        pip_options: null,
      },
      task: "io_lulc:NineClassIOCollection.create_items_task",
      args: {
        asset_chunk_info: {
          uri: "${{ item.uri }}",
          chunk_id: "${{ item.chunk_id }}",
        },
        item_chunkset_uri:
          "blob://ai4edataeuwest/io-lulc-etl-data/pctasks-chunks/io-lulc-9-class/2022-07-28_full/items",
        collection_id: "io-lulc-9-class",
        options: {
          skip_validation: false,
        },
      },
      tags: null,
      environment: {
        AZURE_TENANT_ID: "${{ secrets.task-tenant-id }}",
        AZURE_CLIENT_ID: "${{ secrets.task-client-id }}",
        AZURE_CLIENT_SECRET: "${{ secrets.task-client-secret }}",
      },
      schema_version: "1.0.0",
    },
    {
      id: "ingest-items",
      image: null,
      image_key: "ingest",
      code: null,
      task: "pctasks.ingest_task.task:ingest_task",
      args: {
        content: {
          type: "Ndjson",
          uris: ["${{tasks.create-items.output.ndjson_uri}}"],
        },
        options: {
          insert_group_size: 5000,
          insert_only: false,
        },
      },
      tags: null,
      environment: {
        AZURE_TENANT_ID: "${{ secrets.task-tenant-id }}",
        AZURE_CLIENT_ID: "${{ secrets.task-client-id }}",
        AZURE_CLIENT_SECRET: "${{ secrets.task-client-secret }}",
      },
      schema_version: "1.0.0",
    },
  ],
};

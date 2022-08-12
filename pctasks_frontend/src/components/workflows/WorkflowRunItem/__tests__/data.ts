import { WorkflowRun } from "types";
import { WorkflowRunStatus } from "types/enums";

export const TestWorkflowRunItems: Record<string, WorkflowRun> = {
  completed: {
    run_id: "28dd600b51d24df1afd23a23411b2ca0",
    created: "2022-01-01T00:00:00.000Z",
    updated: "2022-01-01T01:00:00.000Z",
    dataset: "microsoft/ms-landsat-8",
    errors: [],
    links: [],
    status: WorkflowRunStatus.completed,
    trigger_event: null,
    args: {},
  },

  failed: {
    run_id: "2a6204c5f9b2425295a20aaf8b4e242f",
    created: "2022-07-21T15:10:52.983614",
    updated: "2022-07-19T19:01:45.304742",
    dataset: "microsoft/ms-lulc",
    errors: ["Job ingest-collection failed during job preparation."],
    links: [],
    status: WorkflowRunStatus.failed,
  },
  running: {
    run_id: "3ca3c96db2274613a875d7875b1b8e08",
    created: "2022-07-21T15:10:52.984128",
    updated: "2022-07-19T18:45:48.537087",
    dataset: "microsoft/ms-lulc",
    errors: [],
    links: [],
    status: WorkflowRunStatus.running,
  },
  submitted: {
    run_id: "74de29f47a714feab466927b8fcfeac6",
    created: "2022-07-21T15:10:52.984128",
    updated: "2022-07-20T18:45:48.537087",
    dataset: "microsoft/ms-sentinel-2-l2a",
    errors: [],
    links: [],
    status: WorkflowRunStatus.submitted,
  },
};

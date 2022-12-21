import {
  DatasetIdentifier,
  PCTRecord,
  StorageAccountTokens,
  TriggerConfig,
} from "types";
import { WorkflowRunStatus } from "./enums";
import { JobDefinition } from "./jobs";

export type WorkflowDefinition = {
  id: string;
  name: string;
  dataset: DatasetIdentifier | string;
  tokens: Record<string, StorageAccountTokens> | null;
  target_environment: string | null;
  args: string[] | null;
  jobs: Record<string, JobDefinition>;
  on: TriggerConfig | null;
  schema_version: string;
};

export type Workflow = {
  id: string;
  definition: WorkflowDefinition;
};

export type WorkflowRecord = PCTRecord & {
  workflow_id: string;
  workflow: Workflow;

  log_uri: string | null;

  workflow_run_counts: Record<WorkflowRunStatus, number>;
};

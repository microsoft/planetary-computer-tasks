import { CloudEvent, PCTRecord, ResponseLink } from "types";
import {
  JobPartitionRunStatus,
  JobRunStatus,
  TaskRunStatus,
  WorkflowRunStatus,
} from "./enums";

export type RunRecord = PCTRecord & {
  run_id: string;
  links: ResponseLink[] | null;
  errors: string[] | null;
};

export type WorkflowRunRecord = RunRecord & {
  type: string;
  dataset_id: string;
  workflow_id: string;
  status: WorkflowRunStatus;
  trigger_event: CloudEvent | null;
  args: Record<string, any> | null;
  log_uri: string | null;
  jobs: JobRunRecord[];
};

export type JobRunRecord = RunRecord & {
  type: string;
  job_id: string;
  status: JobRunStatus;
  job_partition_counts: Record<JobRunStatus, number>;
};

export type JobParitionRunRecord = RunRecord & {
  type: string;
  job_id: string;
  partition_id: string;
  status: JobPartitionRunStatus;
  tasks: TaskRunRecord[];
};

export type TaskRunRecord = RunRecord & {
  job_id: string;
  task_id: string;
  partition_id: string;
  status: TaskRunStatus;
};

export type RunTimesHumanized = {
  startFriendly: string;
  startFormatted: string;
  duration: number;
  durationFriendly: string;
};

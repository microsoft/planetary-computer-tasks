import { JobRunStatus, LinkRel, TaskRunStatus, WorkflowRunStatus } from "./enums";

export type ResponseLink = {
  rel: LinkRel;
  href: string;
  type?: string;
  title?: string;
};

export type Run = {
  run_id: string;
  created: string;
  updated: string;
  links: ResponseLink[] | null;
  errors: string[] | null;
};

export type WorkflowRun = Run & {
  dataset: string;
  status: WorkflowRunStatus;
  workflow?: WorkflowConfig | null;
  trigger_event?: CloudEvent | null;
  args?: Record<string, any> | null;
};

export type JobRun = Run & {
  job_id: string;
  status: JobRunStatus;
};

export type JobApiDefinition = {
  id: string;
  tasks: [];
  foreach: [];
  notifications: ItemNotificationConfig[] | null;
  needs: string | string[] | null;
};

export type TaskRun = Run & {
  task_id: string;
  job_id: string;
  status: TaskRunStatus;
};

export type TaskApiDefinition = {
  id: string;
  image: string | null;
  image_key: string | null;
  code: CodeConfig | null;
  task: string;
  args: Record<string, any>;
  tags: Record<string, string> | null;
  environment: Record<string, string> | null;
  schema_version: string;
};

export type ForeachConfig = {
  items: string | any[] | null;
};

// TODO
export type ItemNotificationConfig = any;
export type CodeConfig = any;
export type TriggerConfig = any;
export type StorageAccountTokens = any;
export type DatasetIdentifier = any;

// export type JobConfig = {
//   id: string;
//   image: string | null;
//   image_key: string | null;
//   code: CodeConfig | null;
//   task: string;
//   args: Record<string, any>;
//   tags: Record<string, string> | null;
//   environment: Record<string, string> | null;
//   schema_version: string;
// };

export type WorkflowConfig = {
  name: string;
  dataset: DatasetIdentifier | string;
  group_id: string | null;
  tokens: Record<string, StorageAccountTokens> | null;
  target_environment: string | null;
  args: string[] | null;
  jobs: Record<string, JobApiDefinition>;
  on: TriggerConfig | null;
  schema_version: string;
};

export type CloudEvent = {
  spec_version: string;
  type: string;
  source: string;
  subject?: string;
  id: string;
  time: string;
  data_content_type: string;
  data: Record<string, any>;
};

export type RunTimesHumanized = {
  startFriendly: string;
  startFormatted: string;
  duration: number;
  durationFriendly: string;
};

export type IndentLevel = number;

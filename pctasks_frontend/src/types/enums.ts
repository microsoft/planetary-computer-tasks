export enum LinkRel {
  job = "job",
  task = "task",
  log = "log",
}

export enum TaskRunStatus {
  received = "received",
  pending = "pending",
  submitting = "submitting",
  submitted = "submitted",
  starting = "starting",
  running = "running",
  waiting = "waiting",
  completed = "completed",
  failed = "failed",
  cancelled = "cancelled",
}

export enum JobPartitionRunStatus {
  running = "running",
  completed = "completed",
  failed = "failed",
  cancelled = "cancelled",
  pending = "pending",
}

export enum JobRunStatus {
  pending = "pending",
  running = "running",
  completed = "completed",
  failed = "failed",
  cancelled = "cancelled",
  notasks = "notasks",
}

export enum WorkflowRunStatus {
  submitted = "submitted",
  running = "running",
  completed = "completed",
  failed = "failed",
}

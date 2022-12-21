import { TaskRunRecord } from "types/runs";

export const getLogUrl = (task: TaskRunRecord): string | undefined => {
  return task?.links?.find(link => link.rel === "log")?.href;
};

export const equals = (a: TaskRunRecord, b: TaskRunRecord): boolean => {
  return [a.job_id === b.job_id, a.task_id === b.task_id].every(Boolean);
};

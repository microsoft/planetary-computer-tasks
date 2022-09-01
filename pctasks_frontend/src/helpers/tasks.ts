import { TaskRun } from "types";

export const getLogUrl = (task: TaskRun): string | undefined => {
  return task?.links?.find(link => link.rel === "log")?.href;
};

export const equals = (a: TaskRun, b: TaskRun): boolean => {
  return [a.job_id === b.job_id, a.task_id === b.task_id].every(Boolean);
};

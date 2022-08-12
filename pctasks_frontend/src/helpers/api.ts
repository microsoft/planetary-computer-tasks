import axios from "axios";
import { useQuery, QueryFunctionContext } from "@tanstack/react-query";

import { JobRun, TaskRun, WorkflowRun } from "types";
import { API_KEY, API_URL } from "./constants";

const apiClient = axios.create({
  baseURL: API_URL,
});
apiClient.defaults.headers.common["X-API-KEY"] = API_KEY;

const queryConfigDefaults = {
  retry: 2,
  refetchOnWindowFocus: false,
};

// === API Hooks ===

export const useWorkflowRuns = () => {
  return useQuery(["workflows"], getWorkflowRuns, queryConfigDefaults);
};

export const useWorkflowRun = (workflowRunId: string | undefined) => {
  return useQuery(["workflow", workflowRunId], getWorkflowRun, {
    ...queryConfigDefaults,
    enabled: Boolean(workflowRunId),
  });
};

export const useWorkflowJobRuns = (workflowRunId: string | undefined) => {
  return useQuery(["workflowJobRuns", workflowRunId], getWorkflowJobRuns, {
    ...queryConfigDefaults,
    enabled: Boolean(workflowRunId),
    // refetchInterval: 5000,
  });
};

export const useJobTaskRuns = (
  jobRun: JobRun | undefined,
  enabled: boolean = true
) => {
  return useQuery(["jobTaskRuns", jobRun], getJobTaskRuns, {
    ...queryConfigDefaults,
    enabled: Boolean(jobRun) && enabled,
    refetchInterval: 5000,
  });
};

export const useTaskRunLog = (taskRun: TaskRun | undefined) => {
  return useQuery(
    ["taskRunLog", taskRun?.run_id, taskRun?.job_id, taskRun?.task_id],
    getTaskRunLog,
    {
      ...queryConfigDefaults,
      enabled: Boolean(taskRun?.task_id),
      refetchInterval: 2000,
    }
  );
};

// === API Requests ===

const getWorkflowRuns = async (): Promise<WorkflowRun[]> => {
  const response = await apiClient.get(`/runs/`);
  return response.data.runs;
};

const getWorkflowRun = async (
  queryParam: QueryFunctionContext<[string, string | undefined]>
): Promise<WorkflowRun> => {
  const [, workflowRunId] = queryParam.queryKey;
  const response = await apiClient.get(`/runs/${workflowRunId}`);
  return response.data;
};

const getWorkflowJobRuns = async (
  queryParam: QueryFunctionContext<[string, string | undefined]>
): Promise<JobRun[]> => {
  const [, workflowRunId] = queryParam.queryKey;
  const response = await apiClient.get(`/runs/${workflowRunId}/jobs`);
  return response.data.jobs;
};

const getJobTaskRuns = async (
  queryParam: QueryFunctionContext<[string, JobRun | undefined]>
): Promise<TaskRun[]> => {
  const [, jobRun] = queryParam.queryKey;
  const response = await apiClient.get(
    `/runs/${jobRun?.run_id}/jobs/${jobRun?.job_id}/tasks`
  );
  return response.data.tasks;
};

const getTaskRunLog = async (
  queryParam: QueryFunctionContext<
    [string, string | undefined, string | undefined, string | undefined]
  >
): Promise<string> => {
  const [, runId, jobId, taskId] = queryParam.queryKey;
  const response = await apiClient.get(
    `/runs/${runId}/jobs/${jobId}/tasks/${taskId}/logs/run.txt`
  );
  return response.data;
};

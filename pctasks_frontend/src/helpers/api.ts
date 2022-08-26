import { AxiosInstance } from "axios";
import { useQuery, QueryFunctionContext } from "@tanstack/react-query";

import { JobRun, TaskRun, WorkflowRun } from "types";
import { useAuthApiClient } from "components/auth/hooks/useApiClient";

// Create default query options including a client for authentication. Will
// refresh tokens as needed. The authenticated client is accessible via the
// meta property of the query context.
const useQueryConfigDefaults = (enabled?: any[]) => {
  const client = useAuthApiClient();
  const enabledWhen = enabled ? [...enabled, client] : [client];

  return {
    retry: 2,
    refetchOnWindowFocus: false,
    meta: { client },
    enabled: enabledWhen.every(Boolean),
  };
};

const getClient = (context: QueryFunctionContext) =>
  context.meta?.client as AxiosInstance;

// === API Hooks ===

export const useWorkflowRuns = () => {
  const queryConfig = useQueryConfigDefaults([]);
  return useQuery(["workflows"], getWorkflowRuns, queryConfig);
};

export const useWorkflowRun = (workflowRunId: string | undefined) => {
  const queryConfig = useQueryConfigDefaults([workflowRunId]);
  return useQuery(["workflow", workflowRunId], getWorkflowRun, queryConfig);
};

export const useWorkflowJobRuns = (workflowRunId: string | undefined) => {
  const queryConfig = useQueryConfigDefaults([workflowRunId]);
  return useQuery(["workflowJobRuns", workflowRunId], getWorkflowJobRuns, {
    ...queryConfig,
    // refetchInterval: 5000,
  });
};

export const useJobTaskRuns = (
  jobRun: JobRun | undefined,
  enabled: boolean = true
) => {
  const queryConfig = useQueryConfigDefaults([jobRun, enabled]);
  return useQuery(["jobTaskRuns", jobRun], getJobTaskRuns, {
    ...queryConfig,
    refetchInterval: 5000,
  });
};

export const useTaskRunLog = (taskRun: TaskRun | undefined) => {
  const queryConfig = useQueryConfigDefaults([taskRun?.task_id]);
  return useQuery(
    ["taskRunLog", taskRun?.run_id, taskRun?.job_id, taskRun?.task_id],
    getTaskRunLog,
    {
      ...queryConfig,
      refetchInterval: 2000,
    }
  );
};

// === API Requests ===

const getWorkflowRuns = async (
  queryContext: QueryFunctionContext<[string]>
): Promise<WorkflowRun[]> => {
  const client = getClient(queryContext);

  const response = await client.get(`/runs/`);
  return response.data.runs;
};

const getWorkflowRun = async (
  queryContext: QueryFunctionContext<[string, string | undefined]>
): Promise<WorkflowRun> => {
  const [, workflowRunId] = queryContext.queryKey;
  const client = getClient(queryContext);

  const response = await client.get(`/runs/${workflowRunId}`);
  return response.data;
};

const getWorkflowJobRuns = async (
  queryContext: QueryFunctionContext<[string, string | undefined]>
): Promise<JobRun[]> => {
  const [, workflowRunId] = queryContext.queryKey;
  const client = getClient(queryContext);

  const response = await client.get(`/runs/${workflowRunId}/jobs`);
  return response.data.jobs;
};

const getJobTaskRuns = async (
  queryContext: QueryFunctionContext<[string, JobRun | undefined]>
): Promise<TaskRun[]> => {
  const [, jobRun] = queryContext.queryKey;
  const client = getClient(queryContext);

  const response = await client.get(
    `/runs/${jobRun?.run_id}/jobs/${jobRun?.job_id}/tasks`
  );
  return response.data.tasks;
};

const getTaskRunLog = async (
  queryContext: QueryFunctionContext<
    [string, string | undefined, string | undefined, string | undefined]
  >
): Promise<string> => {
  const [, runId, jobId, taskId] = queryContext.queryKey;
  const client = getClient(queryContext);

  const response = await client.get(
    `/runs/${runId}/jobs/${jobId}/tasks/${taskId}/logs/run.txt`
  );
  return response.data;
};

import { AxiosInstance } from "axios";
import { useQuery, QueryFunctionContext } from "@tanstack/react-query";

import { JobRunRecord, TaskRunRecord, WorkflowRunRecord } from "types/runs";
import { useAuthApiClient } from "components/auth/hooks/useApiClient";
import { WorkflowRecord } from "types/workflows";

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

export const useWorkflows = () => {
  const queryConfig = useQueryConfigDefaults([]);
  return useQuery(["workflows"], getRegisteredWorkflows, queryConfig);
};

export const useWorkflow = (workflowId: string | undefined) => {
  const queryConfig = useQueryConfigDefaults([workflowId]);
  return useQuery(["workflow", workflowId], getWorkflowRecord, queryConfig);
};

export const useWorkflowRuns = (
  workflowId: string | undefined,
  isSortDesc: boolean = true
) => {
  const queryConfig = useQueryConfigDefaults([workflowId]);
  return useQuery(
    ["workflowRuns", workflowId, isSortDesc],
    getWorkflowRuns,
    queryConfig
  );
};

export const useWorkflowRun = (workflowRunId: string | undefined) => {
  const queryConfig = useQueryConfigDefaults([workflowRunId]);
  return useQuery(["workflowRun", workflowRunId], getWorkflowRun, queryConfig);
};

export const useWorkflowJobRuns = (workflowRunId: string | undefined) => {
  const queryConfig = useQueryConfigDefaults([workflowRunId]);
  return useQuery(["workflowJobRuns", workflowRunId], getWorkflowJobRuns, {
    ...queryConfig,
    // refetchInterval: 5000,
  });
};

export const useJobTaskRuns = (
  jobRun: JobRunRecord | undefined,
  enabled: boolean = true
) => {
  const queryConfig = useQueryConfigDefaults([jobRun, enabled]);
  return useQuery(["jobTaskRuns", jobRun], getJobTaskRuns, {
    ...queryConfig,
    refetchInterval: 5000,
  });
};

export const useTaskRunLog = (taskRun: TaskRunRecord | undefined) => {
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

const getRegisteredWorkflows = async (
  queryContext: QueryFunctionContext<[string]>
): Promise<WorkflowRecord[]> => {
  const client = getClient(queryContext);

  const response = await client.get(`/workflows/`, {
    params: { sortBy: "updated", order: "desc" },
  });
  return response.data.records;
};

const getWorkflowRecord = async (
  queryContext: QueryFunctionContext<[string, string | undefined]>
): Promise<WorkflowRecord> => {
  const client = getClient(queryContext);
  const [, workflowId] = queryContext.queryKey;

  const response = await client.get(`/workflows/${workflowId}`);
  return response.data.record;
};

const getWorkflowRuns = async (
  queryContext: QueryFunctionContext<[string, string | undefined, boolean]>
): Promise<WorkflowRunRecord[]> => {
  const client = getClient(queryContext);
  const [, workflowId, sortDesc] = queryContext.queryKey;

  const sort = sortDesc ? "desc" : "asc";
  const response = await client.get(`/workflows/${workflowId}/runs`, {
    params: { sortBy: "created", order: sort },
  });
  return response.data.records;
};

const getWorkflowRun = async (
  queryContext: QueryFunctionContext<[string, string | undefined]>
): Promise<WorkflowRunRecord> => {
  const [, workflowRunId] = queryContext.queryKey;
  const client = getClient(queryContext);

  const response = await client.get(`/runs/${workflowRunId}`);
  return response.data;
};

const getWorkflowJobRuns = async (
  queryContext: QueryFunctionContext<[string, string | undefined]>
): Promise<JobRunRecord[]> => {
  const [, workflowRunId] = queryContext.queryKey;
  const client = getClient(queryContext);

  const response = await client.get(`/runs/${workflowRunId}/jobs`);
  return response.data.jobs;
};

const getJobTaskRuns = async (
  queryContext: QueryFunctionContext<[string, JobRunRecord | undefined]>
): Promise<TaskRunRecord[]> => {
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

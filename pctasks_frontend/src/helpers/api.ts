import { AxiosInstance } from "axios";
import { useQuery, QueryFunctionContext } from "@tanstack/react-query";

import {
  JobParitionRunRecord,
  JobRunRecord,
  TaskRunRecord,
  WorkflowRunRecord,
} from "types/runs";
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

export const useWorkflowJobLog = (workflowRunId: string | undefined) => {
  const queryConfig = useQueryConfigDefaults([workflowRunId]);
  return useQuery(["workflowJobRuns", workflowRunId], getWorkflowJobLog, {
    ...queryConfig,
    // refetchInterval: 5000,
  });
};

export const useJobRunPartition = (jobRun: JobRunRecord | undefined) => {
  const queryConfig = useQueryConfigDefaults([jobRun]);
  return useQuery(["jobRunPartition", jobRun], getJobRunPartitions, {
    ...queryConfig,
  });
};

export const useTaskRunLog = (taskRun: TaskRunRecord | undefined) => {
  const queryConfig = useQueryConfigDefaults([taskRun?.task_id]);
  return useQuery(["taskRunLog", taskRun], getTaskRunLog, {
    ...queryConfig,
    refetchInterval: 2000,
  });
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
  return response.data.record;
};

const getWorkflowJobLog = async (
  queryContext: QueryFunctionContext<[string, string | undefined]>
): Promise<JobRunRecord[]> => {
  const [, workflowRunId] = queryContext.queryKey;
  const client = getClient(queryContext);

  const response = await client.get(`/runs/${workflowRunId}/log`);
  return response.data;
};

const getJobRunPartitions = async (
  queryContext: QueryFunctionContext<[string, JobRunRecord | undefined]>
): Promise<JobParitionRunRecord[]> => {
  const [, jobRun] = queryContext.queryKey;
  const client = getClient(queryContext);

  const response = await client.get(
    `/runs/${jobRun?.run_id}/jobs/${jobRun?.job_id}/partitions`
  );
  return response.data.records;
};

const getTaskRunLog = async (
  queryContext: QueryFunctionContext<[string, TaskRunRecord | undefined]>
): Promise<string> => {
  const [, taskRun] = queryContext.queryKey;
  const client = getClient(queryContext);

  const url = [
    `/runs/${taskRun?.run_id}`,
    `/jobs/${taskRun?.job_id}`,
    `/partitions/${taskRun?.partition_id}`,
    `/tasks/${taskRun?.task_id}`,
    `/log`,
  ].join("");

  const response = await client.get(url);
  return response.data;
};

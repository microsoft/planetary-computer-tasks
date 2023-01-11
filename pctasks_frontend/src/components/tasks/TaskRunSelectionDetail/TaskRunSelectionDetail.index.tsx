import { LogOutput } from "components/common/LogOutput/LogOutput.index";
import { useJobRunPartition, useWorkflowRun } from "helpers/api";
import { useParams } from "react-router-dom";

export const TaskRunSelectionDetail = () => {
  const { jobId, partitionId, taskId, workflowRunId } = useParams();
  const { data: workflowRun } = useWorkflowRun(workflowRunId);

  const jobRun = workflowRun?.jobs?.find(job => job.job_id === jobId);
  const { data: partitionRun } = useJobRunPartition(jobRun, partitionId);

  const taskRun = partitionRun?.tasks?.find(task => task.task_id === taskId);

  return <LogOutput taskRun={taskRun} />;
};

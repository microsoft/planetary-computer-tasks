import { DetailPanel } from "components/layout/DetailPanel";
import { useWorkflow, useWorkflowRun } from "helpers/api";
import { useParams } from "react-router-dom";
import { JobDefinitionDetail } from "../JobDefinitionDetail/JobDefinitionDetail.index";
import { JobRunErrors } from "../JobRunErrors/JobRunErrors.index";

export const JobRunSelectionDetail = () => {
  const { jobId, workflowId, workflowRunId } = useParams();
  const { data: workflowRecord } = useWorkflow(workflowId);
  const { data: workflowRun } = useWorkflowRun(workflowRunId);

  const jobRun = workflowRun?.jobs?.find(jobRun => jobRun.job_id === jobId);
  const jobDef = jobId ? workflowRecord?.workflow.definition.jobs[jobId] : undefined;

  return (
    <DetailPanel>
      <JobDefinitionDetail jobDefinition={jobDef} />
      <JobRunErrors run={jobRun} />
    </DetailPanel>
  );
};

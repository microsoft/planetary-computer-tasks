import { useEffect } from "react";
import { Spinner } from "@fluentui/react";

import { usePageTitle } from "components/common/hooks";
import { WorkflowRunList } from "components/runs";
import { useWorkflow, useWorkflowRuns } from "helpers/api";
import { useSelection } from "state/SelectionProvider";
import { AuthPage } from "components/auth";
import { useParams } from "react-router-dom";

export const WorkflowRuns = () => {
  const { workflowId } = useParams();

  const { data: workflowRecord } = useWorkflow(workflowId);
  const { data: workflowRuns, isError, isLoading } = useWorkflowRuns(workflowId);
  const { setSelectedTaskRun } = useSelection();

  const loading = <Spinner />;
  const error = <div>Error</div>;

  useEffect(() => {
    setSelectedTaskRun(undefined);
  }, [setSelectedTaskRun]);

  usePageTitle("Workflow Runs");
  return (
    <div>
      <h2>{workflowRecord?.workflow.definition.name}</h2>
      <AuthPage>
        {isLoading && loading}
        {isError && error}
        {workflowRuns && workflowRecord && (
          <WorkflowRunList workflowRecord={workflowRecord} runs={workflowRuns} />
        )}
      </AuthPage>
    </div>
  );
};

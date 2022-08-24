import { useEffect } from "react";
import { Spinner } from "@fluentui/react";
import { usePageTitle } from "components/common/hooks";
import { WorkflowRunList } from "components/workflows";
import { useWorkflowRuns } from "helpers/api";
import { useSelection } from "state/SelectionProvider";
import { AuthenticatedTemplate, UnauthenticatedTemplate } from "@azure/msal-react";

export const Workflows = () => {
  const { data: workflowRuns, isError, isLoading } = useWorkflowRuns();
  const { setSelectedTaskRun } = useSelection();

  const loading = <Spinner />;
  const error = <div>Error</div>;

  useEffect(() => {
    setSelectedTaskRun(undefined);
  }, [setSelectedTaskRun]);

  usePageTitle("Workflows");
  return (
    <div>
      <h2>Workflows</h2>
      <AuthenticatedTemplate>
        {isLoading && loading}
        {isError && error}
        {workflowRuns && <WorkflowRunList runs={workflowRuns} />}
      </AuthenticatedTemplate>
      <UnauthenticatedTemplate>
        <div>You must be logged in to view this page.</div>
      </UnauthenticatedTemplate>
    </div>
  );
};

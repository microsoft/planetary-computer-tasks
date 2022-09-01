import { useEffect } from "react";
import { Spinner } from "@fluentui/react";

import { usePageTitle } from "components/common/hooks";
import { WorkflowRunList } from "components/workflows";
import { useWorkflowRuns } from "helpers/api";
import { useSelection } from "state/SelectionProvider";
import { AuthPage } from "components/auth";

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
      <AuthPage>
        {isLoading && loading}
        {isError && error}
        {workflowRuns && <WorkflowRunList runs={workflowRuns} />}
      </AuthPage>
    </div>
  );
};

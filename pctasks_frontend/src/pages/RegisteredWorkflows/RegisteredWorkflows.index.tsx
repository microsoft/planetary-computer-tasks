import { usePageTitle } from "components/common/hooks";
import { WorkflowList } from "components/workflows";
import { useWorkflows } from "helpers/api";

export const RegisteredWorkflows = () => {
  usePageTitle("Registered Workflows");
  const { data: workflows, isError } = useWorkflows();
  return (
    <div>
      <h2>Workflows</h2>
      {workflows && <WorkflowList workflows={workflows} />}
      {isError && <div>Error loading workflows</div>}
    </div>
  );
};

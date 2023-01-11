import { mergeStyleSets, Spinner, Stack, StackItem } from "@fluentui/react";
import { Outlet, useParams } from "react-router-dom";

import { WorkflowRunHeader } from "components/runs";
import { JobRunList } from "components/jobs/JobRunList/JobRunList.index";
import { useWorkflow, useWorkflowRun } from "helpers/api";
import { gapRegular, gapSmall } from "styles/global";
import { usePageTitle } from "components/common/hooks";
import { AuthPage } from "components/auth";

export const WorkflowRunDetail = () => {
  const { workflowId, workflowRunId } = useParams();
  const { data: workflowRecord } = useWorkflow(workflowId);
  const { data: workflowRun, isError, isLoading } = useWorkflowRun(workflowRunId);

  const pageTitle = `Workflow ${workflowRun?.dataset_id}: ${workflowRun?.run_id}`;

  const jobs =
    workflowRecord && Object.values(workflowRecord.workflow.definition.jobs);
  const jobRuns = workflowRun?.jobs;

  const runList = (
    <Stack className={styles.container} horizontal tokens={gapRegular}>
      <JobRunList jobs={jobs} runs={jobRuns} />
    </Stack>
  );

  usePageTitle(pageTitle);
  return (
    <AuthPage>
      <WorkflowRunHeader workflow={workflowRecord} run={workflowRun} />
      {isLoading && <Spinner />}
      {isError && <div>Error</div>}

      <Stack className={styles.splitView} horizontal tokens={gapSmall}>
        <StackItem className={styles.panel} shrink={1} grow={1}>
          {workflowRun?.workflow_id && runList}
        </StackItem>
        <Outlet />
      </Stack>
    </AuthPage>
  );
};

const styles = mergeStyleSets({
  container: {
    marginTop: 20,
  },
  splitView: {
    flexGrow: 1,
  },
  panel: {
    width: 500,
  },
});

import { mergeStyleSets, Spinner, Stack, StackItem } from "@fluentui/react";
import { useParams } from "react-router-dom";

import { WorkflowRunHeader } from "components/runs";
import { JobRunList } from "components/jobs/JobRunList/JobRunList.index";
import { useWorkflowJobLog, useWorkflow, useWorkflowRun } from "helpers/api";
import { gapRegular, gapSmall } from "styles/global";
import { TextOutput } from "components/common/TextOutput/TextOutput.index";
import { useSelection } from "state/SelectionProvider";
import { usePageTitle } from "components/common/hooks";
import { AuthPage } from "components/auth";

export const WorkflowRunDetail = () => {
  const { workflowId, workflowRunId } = useParams();
  const { data: workflowRecord } = useWorkflow(workflowId);
  const { data: workflowRun, isError, isLoading } = useWorkflowRun(workflowRunId);
  const { selectedTaskRun } = useSelection();

  const pageTitle = `Workflow ${workflowRun?.dataset_id}: ${workflowRun?.run_id}`;

  // TODO: Get Job Def from workflow def embedded in the url path?
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
      <WorkflowRunHeader run={workflowRun} />
      {isLoading && <Spinner />}
      {isError && <div>Error</div>}

      <Stack className={styles.splitView} horizontal tokens={gapSmall}>
        <StackItem className={styles.panel} shrink={1} grow={1}>
          {workflowRun?.workflow_id && runList}
        </StackItem>
        <TextOutput taskRun={selectedTaskRun} />
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

import { List, mergeStyles, mergeStyleSets, Stack } from "@fluentui/react";

import { JobApiDefinition, JobRun } from "types";
import { borderTop, gapRegular } from "styles/global";
import { JobRunWithTasks } from "../JobRunWithTasks/JobRunWithTasks.index";
import { ParentJobRunItem } from "../ParentJobRunItem/ParentJobRunItem.index";
import { useExpandButton } from "components/common/hooks";
import { useSubJobFilter } from "../hooks/useSubJobFilter";
import { hasSubJobs } from "helpers/jobs";

interface JobRunWithSubJobsProps {
  job: JobApiDefinition;
  jobRuns: JobRun[];
  expanded?: boolean;
}

export const JobRunWithSubJobs: React.FC<JobRunWithSubJobsProps> = ({
  job,
  jobRuns,
  expanded = false,
}) => {
  const { isExpanded, toggleButton } = useExpandButton(expanded);
  const { filterPanel, filteredJobRuns } = useSubJobFilter(jobRuns);

  // Assert this is a job with sub jobs
  if (!hasSubJobs(job)) {
    throw new Error("JobRunWithSubJobs must be used with a job with sub jobs");
  }

  const renderJob = (run: JobRun | undefined) => {
    if (!run) return;

    return (
      <JobRunWithTasks
        key={run.job_id + run.run_id}
        job={job}
        jobRun={run}
        initialTaskRuns={[]}
        indent={1}
      />
    );
  };

  const subJobPanel = <List items={filteredJobRuns} onRenderCell={renderJob} />;

  return (
    <>
      <Stack
        className={styles.item}
        horizontal
        tokens={gapRegular}
        verticalAlign="center"
      >
        {toggleButton}
        <ParentJobRunItem job={job} runs={jobRuns}>
          {filterPanel}
        </ParentJobRunItem>
      </Stack>
      {isExpanded && subJobPanel}
    </>
  );
};

const styles = mergeStyleSets({
  item: mergeStyles(borderTop, {}),
});

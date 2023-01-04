import { List, mergeStyles, mergeStyleSets, Stack } from "@fluentui/react";

import { JobParitionRunRecord, JobRunRecord } from "types/runs";
import { JobDefinition } from "types/jobs";
import { borderTop, gapRegular } from "styles/global";
import { JobRunPartitionWithTasks } from "../JobRunWithTasks/JobRunWithTasks.index";
import { ParentJobRunItem } from "../ParentJobRunItem/ParentJobRunItem.index";
import { useExpandButton } from "components/common/hooks";
import { useSubJobFilter } from "../hooks/useSubJobFilter";
import { hasMultiplePartitions } from "helpers/jobs";

interface JobRunWithSubJobsProps {
  job: JobDefinition;
  jobRun: JobRunRecord;
  jobRunPartitions: JobParitionRunRecord[];
  expanded?: boolean;
}

export const JobRunWithPartitions: React.FC<JobRunWithSubJobsProps> = ({
  job,
  jobRun,
  jobRunPartitions,
  expanded = false,
}) => {
  const { isExpanded, toggleButton } = useExpandButton(expanded);
  const { filterPanel, filteredJobPartitionRuns } =
    useSubJobFilter(jobRunPartitions);

  if (!hasMultiplePartitions(job)) {
    throw new Error(
      "JobRunWithPartitions must be used with a job with multiple partitions (from a foreach)"
    );
  }

  const renderJob = (partition: JobParitionRunRecord | undefined) => {
    if (!partition) return;

    return (
      <JobRunPartitionWithTasks
        key={partition.job_id + partition.run_id}
        job={job}
        jobRun={jobRun}
        jobRunPartition={partition}
        indent={1}
      />
    );
  };

  const subJobPanel = (
    <List items={filteredJobPartitionRuns} onRenderCell={renderJob} />
  );

  return (
    <>
      <Stack
        className={styles.item}
        horizontal
        tokens={gapRegular}
        verticalAlign="center"
      >
        {toggleButton}
        <ParentJobRunItem job={job} run={jobRun}>
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

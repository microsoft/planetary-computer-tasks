import { mergeStyles, mergeStyleSets, Stack } from "@fluentui/react";

import { JobRunItem } from "components/jobs/JobRunItem/JobRunItem.index";
import TaskRunList from "components/tasks/TaskRunList";
import { gapRegular, borderTop, treeIndent } from "styles/global";
import { IndentLevel } from "types";
import { JobParitionRunRecord, JobRunRecord } from "types/runs";
import { JobDefinition } from "types/jobs";
import { useExpandButton } from "components/common/hooks";

interface JobRunPartitionWithTasksProps {
  job: JobDefinition;
  jobRun: JobRunRecord | undefined;
  jobRunPartition: JobParitionRunRecord | undefined;
  expanded?: boolean;
  indent: IndentLevel;
}

export const JobRunPartitionWithTasks: React.FC<JobRunPartitionWithTasksProps> = ({
  job,
  jobRun,
  jobRunPartition,
  expanded = false,
  indent,
}) => {
  const { isExpanded, toggleButton } = useExpandButton(expanded);

  const jobHeader = <JobRunItem job={job} run={jobRun} indent={0} />;
  const styles = getStyles(indent);

  return (
    <>
      <Stack
        horizontal
        className={styles.item}
        tokens={gapRegular}
        verticalAlign="center"
      >
        {toggleButton}
        {jobHeader}
      </Stack>
      <div className={styles.tasks}>
        {isExpanded && (
          <TaskRunList
            tasks={job.tasks}
            taskRuns={jobRunPartition?.tasks || []}
            indent={indent + 2}
          />
        )}
      </div>
    </>
  );
};

const getStyles = (indent: IndentLevel) =>
  mergeStyleSets({
    item: mergeStyles(borderTop, {
      paddingLeft: indent * treeIndent,
    }),
    tasks: mergeStyles({}),
  });

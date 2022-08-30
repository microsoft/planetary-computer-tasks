import { mergeStyles, mergeStyleSets, Stack } from "@fluentui/react";

import { JobRunItem } from "components/jobs/JobRunItem/JobRunItem.index";
import TaskRunList from "components/tasks/TaskRunList";
import { gapRegular, borderTop, treeIndent } from "styles/global";
import { IndentLevel, JobApiDefinition, JobRun, TaskRun } from "types";
import { useExpandButton } from "components/common/hooks";
import { useJobTaskRuns } from "helpers/api";

interface JobRunWithTasksProps {
  job: JobApiDefinition;
  jobRun: JobRun | undefined;
  initialTaskRuns: TaskRun[];
  expanded?: boolean;
  indent: IndentLevel;
}

export const JobRunWithTasks: React.FC<JobRunWithTasksProps> = ({
  job,
  jobRun,
  initialTaskRuns,
  expanded = false,
  indent,
}) => {
  const { isExpanded, toggleButton } = useExpandButton(expanded);
  const { data: taskRuns } = useJobTaskRuns(jobRun, isExpanded);

  console.log("tr", taskRuns);
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
            taskRuns={taskRuns || []}
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

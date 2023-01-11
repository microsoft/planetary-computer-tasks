import { mergeStyles, mergeStyleSets } from "@fluentui/react";
import { RunItem } from "components/common/RunItem/RunItem.index";
import { equals } from "helpers/tasks";
import { borderTop } from "styles/global";
import { IndentLevel, TaskDefinition } from "types";
import { TaskRunRecord } from "types/runs";

interface TaskRunItemProps {
  task: TaskDefinition;
  taskRun: TaskRunRecord | undefined;
  indent?: IndentLevel;
}

export const TaskRunItem: React.FC<TaskRunItemProps> = ({
  task,
  taskRun,
  indent = 1,
}) => {
  const selected = false; //selectedTaskRun && taskRun && equals(taskRun, selectedTaskRun);

  return (
    <div className={styles.item}>
      <RunItem
        title={task.id}
        run={taskRun}
        selected={selected}
        indent={indent}
        href={`job/${taskRun?.job_id}/${taskRun?.partition_id}/tasks/${taskRun?.task_id}`}
      />
    </div>
  );
};

const styles = mergeStyleSets({
  item: mergeStyles(borderTop, {}),
});

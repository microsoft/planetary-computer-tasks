import { mergeStyles, mergeStyleSets } from "@fluentui/react";
import { RunItem } from "components/common/RunItem/RunItem.index";
import { equals } from "helpers/tasks";
import { useSelection } from "state/SelectionProvider";
import { borderTop } from "styles/global";
import { IndentLevel, TaskApiDefinition, TaskRun } from "types";

interface TaskRunItemProps {
  task: TaskApiDefinition;
  taskRun: TaskRun | undefined;
  indent?: IndentLevel;
}

export const TaskRunItem: React.FC<TaskRunItemProps> = ({
  task,
  taskRun,
  indent = 1,
}) => {
  const { selectedTaskRun, setSelectedTaskRun } = useSelection();

  const handleClick = () => {
    setSelectedTaskRun(taskRun);
  };

  const selected = selectedTaskRun && taskRun && equals(taskRun, selectedTaskRun);

  return (
    <div className={styles.item}>
      <RunItem
        title={task.id}
        run={taskRun}
        onClick={handleClick}
        selected={selected}
        indent={indent}
      />
    </div>
  );
};

const styles = mergeStyleSets({
  item: mergeStyles(borderTop, {}),
});

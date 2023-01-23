import { Stack } from "@fluentui/react";
import { IndentLevel, TaskApiDefinition, TaskRun } from "types";
import TaskRunItem from "../TaskRunItem";

interface TaskRunListProps {
  tasks: TaskApiDefinition[];
  taskRuns: TaskRun[];
  indent: IndentLevel;
}

export const TaskRunList: React.FC<TaskRunListProps> = ({
  tasks,
  taskRuns,
  indent,
}) => {
  const items = tasks.map(task => {
    const runs = taskRuns.find(run => run.task_id === task.id);
    return <TaskRunItem key={task.id} task={task} taskRun={runs} indent={indent} />;
  });

  return <Stack>{items}</Stack>;
};

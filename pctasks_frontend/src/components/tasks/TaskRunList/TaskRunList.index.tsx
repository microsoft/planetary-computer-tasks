import { Stack } from "@fluentui/react";
import { IndentLevel, TaskDefinition } from "types";
import { TaskRunRecord } from "types/runs";
import TaskRunItem from "../TaskRunItem";

interface TaskRunListProps {
  tasks: TaskDefinition[];
  taskRuns: TaskRunRecord[];
  indent: IndentLevel;
}

export const TaskRunList: React.FC<TaskRunListProps> = ({
  tasks,
  taskRuns,
  indent,
}) => {
  const items = tasks.map(task => {
    const taskRun = taskRuns.find(run => run.task_id === task.id);
    return (
      <TaskRunItem key={task.id} task={task} taskRun={taskRun} indent={indent} />
    );
  });

  return <Stack>{items}</Stack>;
};

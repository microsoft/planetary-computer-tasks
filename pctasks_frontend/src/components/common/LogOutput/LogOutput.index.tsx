import React from "react";
import { LazyLog } from "react-lazylog";
import { mergeStyleSets, Spinner } from "@fluentui/react";

import { useTaskRunLog } from "helpers/api";
import { TaskRunRecord } from "types/runs";

interface LogOutputProps {
  taskRun: TaskRunRecord | undefined;
}

export const LogOutput: React.FC<LogOutputProps> = ({ taskRun }) => {
  const { data: logText, isLoading } = useTaskRunLog(taskRun);
  const title = taskRun && `${taskRun.job_id} / ${taskRun.task_id}`;

  return (
    <div className={styles.panel}>
      {taskRun && <h4 className={styles.heading}>Task log: {title}</h4>}
      <div className={styles.content}>
        {taskRun && isLoading && <Spinner />}
        {logText && (
          <LazyLog
            enableSearch
            caseInsensitive
            selectableLines
            extraLines={1}
            text={logText}
          />
        )}
      </div>
    </div>
  );
};

const styles = mergeStyleSets({
  panel: {
    display: "flex",
    flexDirection: "column",
    flexGrow: 2,
    width: "100%",
    backgroundColor: "#222222",
    color: "#ffffff",
  },
  content: {
    flexGrow: 1,
  },
  heading: {
    paddingLeft: 30,
  },
});

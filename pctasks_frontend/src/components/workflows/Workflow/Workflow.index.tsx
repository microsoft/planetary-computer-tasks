import { getTheme, mergeStyleSets, Stack, Text } from "@fluentui/react";
import React from "react";
import { WorkflowRecord } from "types/workflows";
import { border } from "styles/global";
import { Link } from "react-router-dom";

interface WorkflowProps {
  workflow: WorkflowRecord;
}

export const Workflow: React.FC<WorkflowProps> = ({ workflow }) => {
  const wf = workflow.workflow.definition;
  return (
    <Stack className={styles.item}>
      {wf.dataset}
      <Link to={`/workflows/${wf.id}`}>{wf.name}</Link>
      <Text>{wf.id}</Text>
    </Stack>
  );
};

const theme = getTheme();
const styles = mergeStyleSets({
  item: [
    border,
    {
      padding: theme.spacing.s1,
    },
  ],
});

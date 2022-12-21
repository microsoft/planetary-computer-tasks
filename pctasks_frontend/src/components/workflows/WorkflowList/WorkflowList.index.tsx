import {
  FontWeights,
  getTheme,
  mergeStyles,
  mergeStyleSets,
  Stack,
  Text,
} from "@fluentui/react";

import { borderRound } from "styles/global";
import { WorkflowRecord } from "types/workflows";
import { Workflow } from "../Workflow/Workflow.index";

interface WorkflowListProps {
  workflows: WorkflowRecord[];
}

export const WorkflowList: React.FC<WorkflowListProps> = ({ workflows }) => {
  const header = (
    <div className={styles.header}>
      <Text className={styles.title}>Registered Workflows </Text>
    </div>
  );
  const workflowItems = workflows.map(workflow => (
    <Workflow workflow={workflow} key={workflow.workflow_id} />
  ));

  return (
    <Stack className={styles.list}>
      {header}
      {workflowItems}
    </Stack>
  );
};

const theme = getTheme();

const styles = mergeStyleSets({
  header: {
    backgroundColor: theme.palette.neutralLighter,
    padding: "15px 10px",
  },
  title: {
    fontWeight: FontWeights.bold,
  },
  item: {
    borderTopColor: theme.palette.neutralLight,
    borderTopStyle: "solid",
    borderTopWidth: 1,
  },
  list: mergeStyles(borderRound, {}),
});

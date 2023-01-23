import {
  FontWeights,
  getTheme,
  mergeStyles,
  mergeStyleSets,
  Stack,
  Text,
} from "@fluentui/react";
import { WorkflowRunItem } from "components/workflows";
import { borderRound } from "styles/global";
import { WorkflowRun } from "types";

interface WorkflowRunListProps {
  runs: WorkflowRun[];
}

export const WorkflowRunList: React.FC<WorkflowRunListProps> = ({ runs }) => {
  const items = runs.map(run => (
    <div className={styles.item} key={run.run_id}>
      <WorkflowRunItem run={run} />
    </div>
  ));
  const header = (
    <div className={styles.header}>
      <Text className={styles.title}>Workflow runs</Text>
    </div>
  );
  return (
    <Stack className={styles.list}>
      {header}
      {items}
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

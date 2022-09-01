import { mergeStyles, mergeStyleSets, Stack, Text } from "@fluentui/react";
import StatusIcon from "components/common/StatusIcon";
import { borderRound, gapRegular } from "styles/global";
import { WorkflowRun } from "types";

interface WorkflowRunHeaderProps {
  run: WorkflowRun | undefined;
}

export const WorkflowRunHeader: React.FC<WorkflowRunHeaderProps> = ({ run }) => {
  return (
    <Stack className={styles.container}>
      <h2 className={styles.heading}>
        <Stack horizontal tokens={gapRegular}>
          <StatusIcon status={run?.status} size="large" />
          <span className={styles.title}>{run?.dataset}</span>
        </Stack>
      </h2>
      <Text className={styles.subtitle} variant="mediumPlus">
        {run?.workflow?.name}
      </Text>
    </Stack>
  );
};

const styles = mergeStyleSets({
  container: mergeStyles(borderRound, {
    padding: 10,
  }),
  title: {
    marginTop: -4,
  },
  subtitle: {
    marginLeft: 32,
  },
  heading: {
    marginBottom: 2,
  },
});

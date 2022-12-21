import { mergeStyles, mergeStyleSets, Stack, Text } from "@fluentui/react";
import StatusIcon from "components/common/StatusIcon";
import { borderRound, gapRegular } from "styles/global";
import { WorkflowRunRecord } from "types/runs";

interface WorkflowRunHeaderProps {
  run: WorkflowRunRecord | undefined;
}

export const WorkflowRunHeader: React.FC<WorkflowRunHeaderProps> = ({ run }) => {
  return (
    <Stack className={styles.container}>
      <h2 className={styles.heading}>
        <Stack horizontal tokens={gapRegular}>
          <StatusIcon status={run?.status} size="large" />
          <span className={styles.title}>{run?.dataset_id}</span>
        </Stack>
      </h2>
      <Text className={styles.subtitle} variant="mediumPlus">
        {run?.workflow_id}
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

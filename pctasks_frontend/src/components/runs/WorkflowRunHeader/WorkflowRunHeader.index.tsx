import { Icon, mergeStyles, mergeStyleSets, Stack, Text } from "@fluentui/react";
import { IconLabel } from "components/common/IconLabel/IconLable.index";
import { RunTimeBlock } from "components/common/RunTimes/RunTimeBlock";
import StatusIcon from "components/common/StatusIcon";
import { borderRound, gapRegular } from "styles/global";
import { WorkflowRunRecord } from "types/runs";
import { WorkflowRecord } from "types/workflows";

interface WorkflowRunHeaderProps {
  workflow: WorkflowRecord | undefined;
  run: WorkflowRunRecord | undefined;
}

export const WorkflowRunHeader: React.FC<WorkflowRunHeaderProps> = ({
  workflow,
  run,
}) => {
  return (
    <Stack className={styles.container}>
      <h2 className={styles.heading}>
        <Stack horizontal tokens={gapRegular}>
          <StatusIcon status={run?.status} size="large" />
          <span className={styles.title}>{workflow?.workflow.definition.name}</span>
        </Stack>
      </h2>
      <Stack horizontal tokens={gapRegular} horizontalAlign="space-between">
        <div>
          <IconLabel
            className={styles.subtitle}
            iconName="Database"
            label={run?.dataset_id}
          />
          <IconLabel
            className={styles.subtitle}
            iconName="Page"
            label={run?.workflow_id}
          />
        </div>
        {run && <RunTimeBlock run={run} />}
      </Stack>
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

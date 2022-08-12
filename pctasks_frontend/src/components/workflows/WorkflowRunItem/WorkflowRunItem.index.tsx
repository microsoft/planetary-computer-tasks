import { FontWeights, getTheme, mergeStyleSets, Stack, Text } from "@fluentui/react";
import { Link } from "react-router-dom";
import StatusIcon from "components/common/StatusIcon";
import { RunTimeBlock } from "components/common/RunTimes/RunTimeBlock";
import { WorkflowRun } from "types";
import { gapRegular } from "styles/global";
import { getShortId } from "helpers/workflows";
import { WorkflowRunItemErrors } from "./WorkflowRunItemErrors";

interface WorkflowRunItemProps {
  run: WorkflowRun;
  selected?: boolean;
}

export const WorkflowRunItem: React.FC<WorkflowRunItemProps> = ({
  run,
  selected = false,
}) => {
  const styles = getStyles(selected);

  const runName = (
    <Link className={styles.title} to={`${run.run_id}`}>
      {run.dataset}
    </Link>
  );
  const runId = (
    <Text className={styles.subTitle} title={run.run_id}>
      {getShortId(run.run_id)}
    </Text>
  );

  const statusSummary =
    run.status === "failed" ? <WorkflowRunItemErrors run={run} /> : null;

  return (
    <Stack horizontal horizontalAlign="space-between" className={styles.root}>
      <Stack horizontal tokens={gapRegular}>
        <StatusIcon status={run.status} />
        <Stack tokens={gapRegular}>
          {runName}
          {runId}
        </Stack>
      </Stack>
      {statusSummary}
      <RunTimeBlock run={run} />
    </Stack>
  );
};

const theme = getTheme();

const getStyles = (selected: boolean) =>
  mergeStyleSets({
    root: [
      {
        padding: theme.spacing.s1,
        backgroundColor: theme.semanticColors.bodyBackground,
        ":hover": {
          backgroundColor: theme.palette.neutralLighterAlt,
        },
      },
      selected && {
        backgroundColor: theme.semanticColors.bodyBackgroundChecked,
      },
    ],
    title: {
      fontWeight: FontWeights.semibold,
      fontSize: theme.fonts.medium,
      color: theme.semanticColors.bodyText,
      textDecoration: "none",
      ":hover": {
        textDecoration: "underline",
      },
    },
    subTitle: {
      fontWeight: FontWeights.light,
    },
  });

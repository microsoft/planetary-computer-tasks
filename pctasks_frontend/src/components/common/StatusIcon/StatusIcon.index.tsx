import { getTheme, keyframes, mergeStyleSets } from "@fluentui/react";
import {
  CheckmarkCircleFilled,
  ErrorCircleFilled,
  ArrowSyncFilled,
  AddCircleFilled,
  DismissCircleFilled,
  SubtractCircleFilled,
  ArrowCircleDownFilled,
  PauseCircleFilled,
  CircleFilled,
} from "@fluentui/react-icons";
import { mergeClassNames } from "helpers/utils";
import {
  JobPartitionRunStatus,
  JobRunStatus,
  TaskRunStatus,
  WorkflowRunStatus,
} from "types/enums";

interface StatusIconProps {
  status:
    | WorkflowRunStatus
    | JobRunStatus
    | JobPartitionRunStatus
    | TaskRunStatus
    | undefined;
  size?: "small" | "medium" | "large";
}

export const StatusIcon: React.FC<StatusIconProps> = ({
  status,
  size = "medium",
}) => {
  const sizeClass = styles[size];
  const icons = {
    completed: (
      <CheckmarkCircleFilled
        className={mergeClassNames(styles.completed, sizeClass)}
      />
    ),
    failed: (
      <ErrorCircleFilled className={mergeClassNames(styles.failed, sizeClass)} />
    ),
    running: (
      <ArrowSyncFilled className={mergeClassNames(styles.running, sizeClass)} />
    ),
    submitted: (
      <AddCircleFilled className={mergeClassNames(styles.submitted, sizeClass)} />
    ),
    cancelled: (
      <DismissCircleFilled className={mergeClassNames(styles.unknown, sizeClass)} />
    ),
    notasks: (
      <SubtractCircleFilled className={mergeClassNames(styles.failed, sizeClass)} />
    ),

    pending: (
      <ArrowCircleDownFilled
        className={mergeClassNames(styles.running, sizeClass)}
      />
    ),
    received: (
      <ArrowCircleDownFilled
        className={mergeClassNames(styles.running, sizeClass)}
      />
    ),
    starting: (
      <ArrowCircleDownFilled
        className={mergeClassNames(styles.running, sizeClass)}
      />
    ),
    submitting: (
      <ArrowCircleDownFilled
        className={mergeClassNames(styles.submitted, sizeClass)}
      />
    ),
    waiting: (
      <PauseCircleFilled className={mergeClassNames(styles.running, sizeClass)} />
    ),
  };

  const statusIcon = status ? (
    icons[status]
  ) : (
    <CircleFilled className={mergeClassNames(styles.unknown, sizeClass)} />
  );

  return <span title={status}>{statusIcon}</span>;
};

const theme = getTheme();
const animation = keyframes({
  "100%": { transform: "rotate(360deg)" },
});

const styles = mergeStyleSets({
  submitted: { color: theme.palette.yellow },
  running: {
    color: theme.palette.yellow,
    animation: `${animation} 3s linear infinite`,
  },
  completed: { color: "rgba(85,163,98,1)" },
  failed: { color: "rgba(205,74,69,1)" },
  unknown: { color: theme.palette.neutralQuaternary },

  small: {
    height: 18,
    width: 18,
  },
  medium: {
    height: 20,
    width: 20,
  },
  large: {
    height: 24,
    width: 24,
  },
});

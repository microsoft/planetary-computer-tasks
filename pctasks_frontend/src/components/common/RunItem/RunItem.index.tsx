import {
  getTheme,
  Link,
  mergeStyles,
  mergeStyleSets,
  Stack,
  Text,
} from "@fluentui/react";
import { formatRunTimes } from "helpers/time";
import { gapRegular, treeIndent } from "styles/global";
import { IndentLevel } from "types";
import { JobRunRecord, TaskRunRecord } from "types/runs";
import { RunTimeDuration } from "../RunTimes/RunDuration";
import StatusIcon from "../StatusIcon";

interface RunItemProps {
  title: string;
  run: JobRunRecord | TaskRunRecord | undefined;
  selected?: boolean;
  indent: IndentLevel;
  onClick?: () => void;
  children?: React.ReactNode;
}
export const RunItem: React.FC<RunItemProps> = ({
  title,
  run,
  selected = false,
  onClick,
  children,
  indent,
}) => {
  const styles = getStyles(selected, indent);
  const runTimes = run ? formatRunTimes(run) : null;
  const duration = runTimes ? (
    <RunTimeDuration className={styles.duration} times={runTimes} showIcon={false} />
  ) : (
    <Text className={styles.duration}>--</Text>
  );

  return (
    <Stack
      horizontal
      className={styles.item}
      tokens={gapRegular}
      horizontalAlign="space-between"
    >
      <Stack horizontal tokens={gapRegular} verticalAlign="start">
        <StatusIcon status={run?.status} />
        <Link onClick={onClick}>
          <Text>{title}</Text>
        </Link>
        {children}
      </Stack>

      {duration}
    </Stack>
  );
};

const theme = getTheme();
const getStyles = (selected: boolean, indent: IndentLevel) => {
  return mergeStyleSets({
    duration: {
      color: theme.palette.neutralTertiary,
      paddingRight: 3,
    },
    item: mergeStyles({
      width: "100%",
      paddingLeft: indent * treeIndent,
      backgroundColor: selected ? theme.palette.neutralLighter : undefined,
      transition: "background-color 0.1s ease-in-out",
      paddingTop: 6,
      paddingBottom: 6,
    }),
  });
};

import { mergeStyles, Stack } from "@fluentui/react";
import { formatRunTimes } from "helpers/time";
import { gapSmall } from "styles/global";
import { RunRecord } from "types/runs";
import { RunTimeDuration } from "./RunDuration";
import { RunTimeStarted } from "./RunStarted";

interface RunTimeBlockProps {
  run: RunRecord;
}

export const RunTimeBlock: React.FC<RunTimeBlockProps> = ({ run }) => {
  const runTimes = formatRunTimes(run);
  const started = <RunTimeStarted times={runTimes} />;
  const duration = <RunTimeDuration times={runTimes} />;

  return (
    <Stack className={className} tokens={gapSmall} horizontalAlign="start">
      {started}
      {duration}
    </Stack>
  );
};

const className = mergeStyles({
  minWidth: 110,
});

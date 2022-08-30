import { Stack, Text } from "@fluentui/react";
import { gapSmall } from "styles/global";
import { RunTimesHumanized } from "types";

interface RunTimeEntryProps extends React.HTMLAttributes<HTMLElement> {
  icon?: React.ReactNode;
  text: string;
  title?: string;
}

export interface RunTimeProps extends React.HTMLAttributes<HTMLElement> {
  times: RunTimesHumanized;
  showIcon?: boolean;
}

export const RunTimeEntry: React.FC<RunTimeEntryProps> = ({
  icon,
  text,
  title,
  className,
}) => {
  return (
    <Stack title={title} horizontal tokens={gapSmall}>
      {icon}
      <Text className={className} block>
        {text}
      </Text>
    </Stack>
  );
};

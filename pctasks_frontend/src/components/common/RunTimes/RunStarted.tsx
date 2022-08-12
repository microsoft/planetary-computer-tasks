import { CalendarLtr20Regular } from "@fluentui/react-icons";
import { RunTimeEntry, RunTimeProps } from "./RunTimeEntry";

export const RunTimeStarted: React.FC<RunTimeProps> = ({ times }) => {
  return (
    <RunTimeEntry
      icon={<CalendarLtr20Regular />}
      text={times.startFriendly}
      title={times.startFormatted}
    />
  );
};

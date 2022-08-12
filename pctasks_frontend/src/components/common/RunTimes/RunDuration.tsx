import { Clock20Regular } from "@fluentui/react-icons";
import { RunTimeEntry, RunTimeProps } from "./RunTimeEntry";

export const RunTimeDuration: React.FC<RunTimeProps> = ({
  times,
  showIcon = true,
  className = "",
}) => {
  const icon = showIcon ? <Clock20Regular /> : null;
  return (
    <RunTimeEntry className={className} icon={icon} text={times.durationFriendly} />
  );
};

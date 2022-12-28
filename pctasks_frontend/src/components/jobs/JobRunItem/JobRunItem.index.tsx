import { IndentLevel } from "types";
import { JobRunRecord } from "types/runs";
import { JobDefinition } from "types/jobs";
import { RunItem } from "components/common/RunItem/RunItem.index";

interface JobRunItemProps {
  job: JobDefinition;
  run: JobRunRecord | undefined;
  indent: IndentLevel;
  children?: React.ReactNode;
}

export const JobRunItem: React.FC<JobRunItemProps> = ({
  job,
  run,
  indent,
  children,
}) => {
  const title = run?.job_id || job.id;

  return (
    <RunItem title={title} run={run} indent={indent}>
      {children}
    </RunItem>
  );
};

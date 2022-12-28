import { JobDefinition } from "types/jobs";
import { JobRunRecord } from "types/runs";
import { JobRunItem } from "../JobRunItem/JobRunItem.index";

interface ParentJobRunItemProps {
  job: JobDefinition;
  run: JobRunRecord;
  children: React.ReactNode;
}

export const ParentJobRunItem: React.FC<ParentJobRunItemProps> = ({
  job,
  run,
  children,
}) => {
  return (
    <JobRunItem job={job} run={run} indent={0}>
      {children}
    </JobRunItem>
  );
};

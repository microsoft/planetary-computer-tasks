import { JobDefinition } from "types/jobs";
import { JobRunRecord } from "types/runs";
import { JobRunItem } from "../JobRunItem/JobRunItem.index";

interface ParentJobRunItemProps {
  job: JobDefinition;
  runs: JobRunRecord[];
  children: React.ReactNode;
}

export const ParentJobRunItem: React.FC<ParentJobRunItemProps> = ({
  job,
  runs,
  children,
}) => {
  return (
    <JobRunItem job={job} run={undefined} indent={0}>
      {children}
    </JobRunItem>
  );
};

import { makeSyntheticJobRun } from "helpers/jobs";
import { JobApiDefinition, JobRun } from "types";
import { JobRunItem } from "../JobRunItem/JobRunItem.index";

interface ParentJobRunItemProps {
  job: JobApiDefinition;
  runs: JobRun[];
  children: React.ReactNode;
}

export const ParentJobRunItem: React.FC<ParentJobRunItemProps> = ({
  job,
  runs,
  children,
}) => {
  const synthRun = makeSyntheticJobRun(job.id, runs);

  return (
    <JobRunItem job={job} run={synthRun} indent={0}>
      {children}
    </JobRunItem>
  );
};
